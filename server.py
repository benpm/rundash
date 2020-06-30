import sys
import os
from math import *
import string
import time
from enum import IntEnum as enum
import flask
import flask_socketio as io
import msgpack
import gzip
import json
import generation
import importlib
from py_gjapi import GameJoltTrophy
from game_classes import Player, Actor, Win

# Usage
print("Usage: %s [port]" % sys.argv[0])

# Helper functions
def pack(obj):
    "Packs any object using msgpack"
    return msgpack.packb(obj)

def unpack(msg):
    "Unpacks a websocket message"
    return msgpack.unpackb(bytearray(msg["data"]))

def send(recipient, msgtype, data):
    "Sends a message (to a room or a single client's SID)"
    sock.emit(
        "msg", {"data": pack([msgtype, data])}, room=recipient, namespace="/")

def distance(x1, y1, x2, y2):
    return sqrt((y2 - y1)**2 + (x2 - x1)**2)

def set_room(player, room, namespace = "/"):
    with app.app_context():
        io.join_room(room, player.sid, namespace)

    player.room = room

def leave_room(player, room, namespace = "/"):
    with app.app_context():
        io.leave_room(room, player.sid, "/")

def close_room(room, namespace = "/"):
    with app.app_context():
        io.close_room(room, namespace)

def get_next_game_time():
    t = GAME_TICKS
    for game in games:
        t = min(game.timer, t)
    return t

# Setup server app
app = flask.Flask(__name__, static_url_path="/public")

# Setup websocket app
players = {}
games = []
waitqueue = []
maxgames = 10
sock = io.SocketIO(app)

# Setup GameJolt stuff
gj = None
if os.path.exists("gamejolt.json"):
    with open("gamejolt.json", "r+") as file:
        gj_info = json.load(file)
        if "game_id" in gj_info and "private_key" in gj_info:
            gj = GameJoltTrophy("", "", gj_info["game_id"], gj_info["private_key"])
            print("[GAMEJOLT]", "Ready for API usage!")
        else:
            print("[GAMEJOLT]", "Missing game_id / private_key from gamejolt.json file!")
else:
    print("[GAMEJOLT]", "Missing gamejolt.json file!")

# Globals
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
TICK_SEC = 20
TICK = 1.0 / TICK_SEC
GAME_TICKS = TICK_SEC * 30
TTL = TICK_SEC * 7
MAX_PLAYERS = 8
HSPEED = 6.5
VSPEED = 18
GRAVITY = 0.8
DRAG = 0.35
HVEL = HSPEED * (pow(DRAG, 4) + pow(DRAG, 3) + pow(DRAG, 2) + DRAG + 1)
msg = enum("msg", "join leave game update login init endgame win dead info leaderboard lobbyinfo")

# Main Game class
class Game(object):
    def __init__(self, game_num, tick_sec, game_ticks):
        self.num = game_num
        self.room = "game_{}".format(self.num)
        self.title = "[GAME {}]".format(self.num)

        self.actors = []
        self.players = []

        self.started = False
        self.finished = False
        self.ttl = TTL

        self.timer = game_ticks
        self.tick_sec = tick_sec
        self.gametime = 0

        importlib.reload(generation)
        #self.level = generation.build_level(random.choice(["horizontal", "vertical"]))
        self.level = generation.build_level("classic")

        games.append(self)
        print(self.title, "created")
        send("lobby", msg.lobbyinfo, f"{len(games)} games;{len(players)} online")

    def addplayer(self, player):
        assert self.started == False
        assert player.game == None, player.name
        assert player.room == "lobby"

        # Set ttl back to max to wait for more players
        self.ttl = TTL

        # Add player to room
        player.game = self
        player.gindex = len(self.players)

        set_room(player, self.room)

        player.update(self.level.spawnx, self.level.spawny, 0, 0)

        send(player.sid, msg.join, {
            "number": self.num,
            "gid": player.gindex,
            "x": self.level.spawnx,
            "y": self.level.spawny
        })

        self.players.append(player)
        print(self.title, player.name, "joined")

    def removeplayer(self, player, goodbye=True):
        assert player.game == self, player.game.title

        if goodbye:
            send(self.room, msg.leave, {"index": player.gindex})
            self.players.remove(player)

        print(self.title, player.name, "exited")
        set_room(player, "lobby")
        player.reset_game_state()
    
    def sendplayerdeath(self, player):
        send(self.room, msg.dead, {
            "gid": player.gindex, 
            "x": player.x,
            "y": player.y})

    def start(self):
        self.started = True
        self.gametime = 20 * 60

        send(self.room, msg.game, {
            "number": self.num,
            "players": [{"name": p.name, "gid": p.gindex} for p in self.players],
            "data": self.level.compressed
        })

        print(self.title, "started")

    def stop(self):
        self.started = False
        self.finished = True

        close_room(self.room)
        print(self.title, "stopped")
        send("lobby", msg.lobbyinfo, f"{len(games)} games;{len(players)} online")

    def finish(self):
        print(self.title, "finished")
        wins = []

        # Add Wins
        for player in self.players:
            if player.win:
                wins.append({
                    "name": player.name,
                    "sid": player.sid,
                    "time": player.win.time
                })

        # Sort wins and players
        wins = sorted(wins, key=lambda win: win["time"])

        # GameJolt wins
        for win in wins[:3]:
            player = players[win["sid"]]
            player.wins += 1
            if gj:
                gj.addScores(str(player.wins), player.wins, 519293, guest=True, guestname=player.name)
                print("[GAMEJOLT]", player.name, player.wins)

        # Add DNFs
        for player in self.players:
            if not player.win:
                wins.append({
                    "name": player.name,
                    "sid": player.sid,
                    "time": 0
                })

        # Remove all players
        for player in self.players:
            self.removeplayer(player, goodbye=False)

        send(self.room, msg.endgame, wins)

        # Stop game
        self.stop()

    def update(self):
        if self.started == False:
            if len(self.players) > 1:
                self.ttl -= 1
                if self.ttl % TICK_SEC == 0:
                    send(self.room, msg.info, f"lobby {self.num};starting in {self.ttl // TICK_SEC}s;{len(self.players)} joined;{len(players)} online")
                if self.ttl <= 0:
                    self.start()
            else:
                t = get_next_game_time()
                if t != GAME_TICKS:
                    m = f"next game in {get_next_game_time() // TICK_SEC}s"
                else:
                    m = f"waiting for players"
                send(self.room, msg.info, f"lobby {self.num};{m};{len(self.players)} joined;{len(players)} online")
            return

        # Check if there are no players left
        if len(self.players) <= 1:
            print(self.title, "empty game! %d players left" % len(self.players))
            send(self.room, msg.login, "your last opponent left the game!")
            self.finish()

        # Send position / velocity updates to players
        update = {
            "gid": [],
            "x": [],
            "y": [],
            "vx": [],
            "vy": [],
            "time": ceil(self.timer / self.tick_sec)
        }

        for player in self.players:
            update["gid"].append(player.gindex)
            update["x"].append(player.x)
            update["y"].append(player.y)
            update["vx"].append(player.vx)
            update["vy"].append(player.vy)

        send(self.room, msg.update, update)

        # Countdown until time is up
        self.timer -= 1
        if self.timer <= 0:
            self.finish()

        # Increment player counters
        for player in self.players:
            player.timer += 1

## Server setup
# Root serving
@app.route("/")
def index():
    return flask.send_file("./public/index.html")

# Static file serving
@app.route("/<path:path>")
def sendfile(path):
    return flask.send_from_directory("public", path)

# Websocket recieve
@sock.on("msg")
def recieve(message):
    "Recieve a message from a client"
    player = players[flask.request.sid]
    game = player.game
    data = unpack(message)
    info = data[1]

    if data[0] == msg.update:
        player.update(info["x"], info["y"], info["vx"], info["vy"])
    elif data[0] == msg.login:
        #TODO: login using GameJolt API
        assert player not in waitqueue
        assert game == None
        nickname = info

        # Verify nickname
        if len(nickname) < 3 or len(nickname) > 8:
            send(player.sid, msg.login,
                 "Name must be between 3 and 8 characters long!")
            nickname = ""
        for char in nickname:
            if char not in string.ascii_letters and char not in string.digits:
                send(player.sid, msg.login, "Name cannot contain '%s'!" % char)
                nickname = ""
                break

        # If no issue, add to waitqueue
        if nickname:
            player.name = nickname
            print("[SERVER]", nickname, "logged in")
            waitqueue.append(player)
    elif data[0] == msg.win:
        assert game
        if player.win == None:
            player.win = Win(game, player, player.timer)
        elif player.win.time > player.timer:
            player.win.time = player.timer
        send(player.sid, msg.win, {"time": player.timer})
        # Send leaderboard to all players in current game
        send(game.room, msg.leaderboard,
            [f"{p.name} [{p.win.time // TICK_SEC}s]" for p in sorted([p for p in game.players if p.win != None], key=lambda p: p.win.time)]
        )
        player.timer = 0
    elif data[0] == msg.game:
        assert player not in waitqueue
        waitqueue.append(player)
    elif data[0] == msg.dead:
        assert game != None
        player.death()

# Websocket connect
@sock.on("connect")
def connect():
    "New connected client"
    sid = flask.request.sid
    print("[SERVER]", "connection:", flask.request.referrer, "sid:", flask.request.sid)
    players[sid] = player = Player(sid, 2, 8, "lobby")
    set_room(player, player.room)
    send(player.sid, msg.init, {
        "sid": sid,
        "hspeed": HSPEED,
        "vspeed": VSPEED,
        "gravity": GRAVITY,
        "drag": DRAG
        })
    send("lobby", msg.lobbyinfo, f"{len(games)} games;{len(players)} online")

# Websocket disconnect
@sock.on("disconnect")
def disconnect():
    "Client disconnected"
    player = players[flask.request.sid]
    print("[SERVER]", player.name, "disconnected")
    if player.game:
        # Remove player from their game
        player.game.removeplayer(player)

    # Remove player from waitqueue
    if player in waitqueue:
        waitqueue.remove(player)

    for room in io.rooms(player.sid):
        leave_room(player, room)

    players.pop(player.sid)
    send("lobby", msg.lobbyinfo, f"{len(games)} games;{len(players)} online")

# Main game loop
def gameloop():
    "The main game loop"
    dtick = 0

    print("[SERVER]", "started gameloop")
    while True:
        # Start timer
        dtick = time.time()

        # Update games
        for game in games[:]:
            if game.finished is True:
                print("[SERVER]", "removing game", game.num)
                games.remove(game)
                del game
                print("[SERVER]", len(games), "games remain")
            else:
                game.update()

        # Update game queue
        for player in waitqueue[:]:
            if len(games) <= maxgames:
                waitqueue.remove(player)

                # Attempt to add to existing game
                n = 0
                for game in games:
                    n = max(n, game.num)
                    if not game.started and len(game.players) < MAX_PLAYERS:
                        game.addplayer(player)
                        break
                else:
                    game = Game(n + 1, TICK_SEC, GAME_TICKS)
                    game.addplayer(player)

        # Wait delta time
        dtick = time.time() - dtick
        if dtick < TICK: sock.sleep(TICK - dtick)

# Begin
if __name__ == "__main__":
    debugMode = len(sys.argv) > 2 and sys.argv[2] == "debug"

    if not debugMode:
        print("[SERVER]", "RELEASE MODE uglifying js...")
        os.system("uglifyjs -c -m -e -o ./public/js/index.min.js -- ./game.js")
    else:
        print("[SERVER]", "DEBUG MODE copying js...")
        os.system("cp ./game.js ./public/js/index.min.js")
    
    print("[SERVER]", f"starting on port {PORT}...")
    gamethread = sock.start_background_task(gameloop)
    sock.run(app, host="0.0.0.0", port=PORT)
 