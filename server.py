import sys
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
import random
from game_classes import Player, Actor, Win

# Usage
print("Usage: %s [TTL (seconds)]" % sys.argv[0])

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

# Setup server app
app = flask.Flask(__name__, static_url_path="/public")

# Setup websocket app
players = {}
games = []
waitqueue = []
maxgames = 10
sock = io.SocketIO(app)

# Globals
TICK_SEC = 20
TICK = 1.0 / TICK_SEC
GAME_TICKS = TICK_SEC * 60
TTL = TICK_SEC * 4
if len(sys.argv) > 1: TTL = int(sys.argv[1]) * TICK_SEC
HSPEED = 6.5
VSPEED = 18
GRAVITY = 0.8
DRAG = 0.35
HVEL = HSPEED * (pow(DRAG, 4) + pow(DRAG, 3) + pow(DRAG, 2) + DRAG + 1)
msg = enum("msg", "join leave game update login init endgame win dead")

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

    def addplayer(self, player):
        assert self.started == False
        assert player.game == None, player.name
        assert player.room == "lobby"

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

        # Sort wins
        for i in range(1, len(wins)):
            j = i
            while j > 0 and wins[j - 1]["time"] > wins[j]["time"]:
                temp = wins[j]
                wins[j] = wins[j - 1]
                wins[j - 1] = temp
                j -= 1

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
                if self.ttl <= 0:
                    self.start()
            return

        # Check if there are no players left
        if len(self.players) <= 1:
            print("empty game! %d players left" % len(self.players))
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
            print(nickname, "logged in")
            waitqueue.append(player)
    elif data[0] == msg.win:
        assert game
        if player.win == None:
            player.win = Win(game, player, player.timer)
        elif player.win.time > player.timer:
            player.win.time = player.timer
        send(player.sid, msg.win, {"time": player.timer})
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
    print("[SERVER]", "connection:", flask.request.referrer)
    players[sid] = player = Player(sid, 2, 8, "lobby")
    send(player.sid, msg.init, {
        "sid": sid,
        "hspeed": HSPEED,
        "vspeed": VSPEED,
        "gravity": GRAVITY,
        "drag": DRAG
        })

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

# Main game loop
def gameloop():
    "The main game loop"
    dtick = 0
    game_number = 0

    print("[SERVER]", "started gameloop")
    while True:
        # Start timer
        dtick = time.time()

        # Update games
        for game in games:
            if game.finished is True:
                games.remove(game)
                del game
            else:
                game.update()

        # Update game queue
        for player in waitqueue:
            if len(games) <= maxgames:
                waitqueue.remove(player)
                added = False

                # Attempt to add to existing game
                for game in games:
                    if not game.started:
                        game.addplayer(player)
                        break
                else:
                    game = Game(game_number, TICK_SEC, GAME_TICKS)
                    game_number += 1
                    game.addplayer(player)

                break

        # Wait delta time
        dtick = time.time() - dtick
        if dtick < TICK: sock.sleep(TICK - dtick)

# Begin
if __name__ == "__main__":
    print("[SERVER]", "starting...")
    gamethread = sock.start_background_task(gameloop)
    sock.run(app, host="0.0.0.0", port=8000)
