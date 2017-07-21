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

def set_room(player, room):
    with app.app_context():
        io.join_room(room, player.sid, "/")
    
    player.room = room

# Setup server app
app = flask.Flask(__name__, static_url_path="/public")

# Setup websocket app
players = {}
games = []
waitqueue = []
maxgames = 10
sock = io.SocketIO(app)

# Globals
GRID = 10
TICK_SEC = 20
TICK = 1 / TICK_SEC
GAME_TICKS = TICK_SEC * 60
TTL = TICK_SEC * 4
HSPEED = 6.5
VSPEED = 18
GRAVITY = 0.8
DRAG = 0.35
HVEL = HSPEED * (pow(DRAG, 4) + pow(DRAG, 3) + pow(DRAG, 2) + DRAG + 1)
msg = enum("msg", "join leave game update login init endgame win dead")

# Game structures
class Game(object):
    def __init__(self):
        self.num = len(games)
        self.room = "game_{}".format(self.num)
        self.title = "[GAME {}]".format(self.num)
        self.players = []
        self.started = False
        self.ttl = TTL
        self.gametime = 0
        self.actors = []
        self.timer = GAME_TICKS

        importlib.reload(generation)
        self.level = generation.build_level("vertical")

        games.append(self)
        print(self.title, "created")

    def addplayer(self, player):
        assert self.started == False
        assert player.game == None
        assert player.room == "lobby"

        # Add player to room
        player.game = self
        player.gindex = len(self.players)
        set_room(player, self.room)
        # player.room = self.room
        player.update(self.level.spawnx, self.level.spawny, 0, 0)
        player.send(msg.join, {
            "number": self.num,
            "gid": player.gindex,
            "x": self.level.spawnx,
            "y": self.level.spawny
        })
        print(self.title, player.name, "joined")
        self.players.append(player)

    def removeplayer(self, player, goodbye=True):
        assert player.game == self, player.game.title
        if player in self.players:
            if goodbye:
                send(self.room, msg.leave, {"index": player.gindex})
                self.players.remove(player)
            print(self.title, player.name, "exited")
            set_room(player, "lobby")
            # player.room = "lobby"
            
            player.game = None
            player.gindex = -1
            player.timer = 0

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
        self.players.clear()
        self.started = False
        print(self.title, "stopped")

    def finish(self):
        print(self.title, "finished")
        wins = []

        # Add DNFs
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
            self.removeplayer(player, goodbye=False)

        # Stop game
        self.players.clear()
        send(self.room, msg.endgame, wins)
        self.stop()

    def update(self):
        if self.started == False:
            if len(self.players) > 1:
                self.ttl -= 1
                if self.ttl <= 0:
                    self.start()
            return True
        else:
            # Check if there are no players left
            if len(self.players) <= 1:
                print("empty game! %d players left" % len(self.players))
                self.finish()
                return False

            # Send position / velocity updates to players
            update = {
                "gid": [],
                "x": [],
                "y": [],
                "vx": [],
                "vy": [],
                "time": ceil(self.timer / TICK_SEC)
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
                return False

            # Increment player counters
            for player in self.players:
                player.timer += 1

            return True

class Actor(object):
    "Character"

    def __init__(self, x, y):
        # Position
        self.x = x * GRID
        self.y = y * GRID
        # Velocity
        self.vx = 0
        self.vy = 0
        # Change in position
        self.dx = 0
        self.dy = 0

    def update(self, x, y, vx, vy):
        self.dx = x - self.x
        self.dy = y - self.y
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


class Player(Actor):
    def __init__(self, sid, x, y, room = "lobby"):
        super(Player, self).__init__(x, y)

        # Nickname
        self.name = "player"

        # Session ID string
        self.sid = sid

        # Game
        self.gindex = -1
        self.game = None
        self.win = None

        # Room (lobby by default)
        self.room = room

        # Game Race Timer
        self.timer = 0

    def send(self, msgtype, data):
        send(self.sid, msgtype, data)


class Win(object):
    "Represents a win in a game"

    def __init__(self, game, player, time):
        self.game = game
        self.time = time
        self.player = player

    def obj(self):
        return {
            "name": self.player.name,
            "time": floor(self.time / TICK_SEC),
            "sid": self.player.sid
        }

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
        player.update(info[b"x"], info[b"y"], info[b"vx"], info[b"vy"])
    elif data[0] == msg.login:
        #TODO: login using GameJolt API
        assert player not in waitqueue
        assert game == None
        player.name = info.decode() if len(info) > 0 else player.name
        waitqueue.append(player)
    elif data[0] == msg.win:
        assert game
        if player.win == None:
            player.win = Win(game, player, player.timer)
        elif player.win.time > player.timer:
            player.win.time = player.timer
        player.send(msg.win, {"time": player.timer})
        player.timer = 0
    elif data[0] == msg.game:
        assert player not in waitqueue
        waitqueue.append(player)
    elif data[0] == msg.dead:
        assert game != None
        player.timer = 0

# Websocket connect
@sock.on("connect")
def connect():
    "New connected client"
    sid = flask.request.sid
    print("[SERVER]", "connection:", flask.request.referrer)
    players[sid] = player = Player(sid, 2, 8, "lobby")
    player.send(msg.init, {
        "sid": sid,
        "hspeed": HSPEED,
        "vspeed": VSPEED,
        "gravity": GRAVITY,
        "drag": DRAG
        })
    #waitqueue.append(player)

# Websocket disconnect
@sock.on("disconnect")
def disconnect():
    "Client disconnected"
    player = players[flask.request.sid]
    print("[SERVER]", player.name, "disconnected")
    if player.game:
        # Remove player from their game
        player.game.removeplayer(player)
    else:
        # Remove player from waitqueue
        if player in waitqueue: waitqueue.remove(player)
    io.leave_room(player.room)
    players.pop(player.sid)

# Main game loop
def gameloop():
    "The main game loop"
    dtick = 0
    print("[SERVER]", "started gameloop")
    while True:
        # Start timer
        dtick = time.clock()

        # Update games
        ngames = len(games)
        for i in range(ngames):
            if not games[ngames - 1 - i].update():
                del games[ngames - 1 - i]

        # Update game queue
        for player in waitqueue:
            if len(games) <= maxgames:
                waitqueue.remove(player)
                added = False

                # Attempt to add to existing game
                for game in games:
                    if not game.started:
                        game.addplayer(player)
                        added = True
                        break

                # Add new game
                if not added:
                    game = Game()
                    game.addplayer(player)

                break

        # Wait delta time
        dtick = time.clock() - dtick
        if dtick < TICK: sock.sleep(TICK - dtick)

# Begin
if __name__ == "__main__":
    print("[SERVER]", "starting...")
    gamethread = sock.start_background_task(gameloop)
    sock.run(app, host="0.0.0.0", port=8080)
