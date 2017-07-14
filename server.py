import time
from enum import IntEnum as enum
import flask
import flask_socketio as io
import msgpack
import gzip
import json

# Helper functions
def pack(obj):
    "Packs any object using msgpack"
    return msgpack.packb(obj)

def unpack(msg):
    "Unpacks a websocket message"
    return msgpack.unpackb(bytearray(msg["data"]))

def send(recipient, msgtype, data):
    "Sends a message (to a room or a single client's SID)"
    sock.emit("msg", {"data": pack([msgtype, data])}, room=recipient, namespace="/")

# Setup server app
app = flask.Flask(__name__, static_url_path="/public")

# Setup websocket app
players = {}
games = []
waitqueue = []
maxgames = 10
sock = io.SocketIO(app)

# Setup game globals
server = {"ticktime": 1/20}
msg = enum("msg", "join leave game update login init endgame")

# Game structures
class Game(object):
    def __init__(self):
        self.num = len(games)
        self.room = "game_%d" % self.num
        self.players = []
        self.started = False
        self.ttl = 40
        self.gametime = 0
        self.props = []
        self.actors = []
        self.spawnx = 0
        self.spawny = 0
        self.compressed = None
        self.generate()
        games.append(self)
        print("created", self.room)

    def addplayer(self, player):
        assert self.started == False
        assert player.get_room() == "lobby"

        # Add player to room
        player.gindex = len(self.players)
        player.set_room(self.room)
        player.send(msg.join, {"number": self.num, "gid": player.gindex})
        print("added player to", self.room)
        self.players.append(player)

    def removeplayer(self, player):
        assert player.get_room() == self.room
        assert len(self.players) > 0
        self.players.remove(player)
        send(self.room, msg.leave, {"index": player.gindex})
        print("removed %s from %s, %d left" % (player.sid, self.room, len(self.players)))

    def start(self):
        self.started = True
        self.gametime = 20 * 60
        send(self.room, msg.game, {
            "number": self.num,
            "players": len(self.players),
            "data": self.compressed})
        print("started", self.room)

    def stop(self):
        for i in range(len(games)):
            if games[i].num == self.num:
                print("deleted", games[i].room, self.room)
                del games[i]
                break
        self.started = False
        print("stopped", self.room, " games left:", games)

    def update(self):
        if self.started == False:
            if len(self.players) > 1:
                self.ttl -= 1
                if self.ttl <= 0:
                    self.start()
        else:
            # Check if there are no players left
            if len(self.players) == 0:
                self.stop()
                return

            # Send position / velocity updates to players
            update = {"gid": [], "x": [], "y": [], "vx": [], "vy": []}
            for player in self.players:
                update["gid"].append(player.gindex)
                update["x"].append(player.x)
                update["y"].append(player.y)
                update["vx"].append(player.vx)
                update["vy"].append(player.vy)
            send(self.room, msg.update, update)

            #todo: count down until time is up (1 minute)

        # Static file serving
    def generate(self):
        self.props.append(Prop(-64, 16, 128, 2, "platform"))
        self.props.append(Prop(-60, 0, 2, 14, "platform goal"))
        self.props.append(Prop(20, 14, 10, 2, "spike"))
        self.compress()
    def compress(self):
        props = [prop.asdict() for prop in self.props]
        self.compressed = json.dumps({"props": props})
class Prop(object):
    "Static object on stage. Position example: [x, y]; and size: [width, height]."
    def __init__(self, x, y, w, h, proptype):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.type = proptype

    def update(self, x, y):
        self.x = x
        self.y = y

    def asdict(self):
        "Returns self as dictionary object, useful for serialization"
        return {
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "w": self.width,
            "h": self.height}
class Actor(object):
    "Character"
    def __init__(self, x, y):
        # Position
        self.x = x
        self.y = y
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
    def __init__(self, sid, x, y, room="lobby"):
        super(Player, self).__init__(x, y)

        # Session ID string
        self.sid = sid

        # Game index
        self.gindex = -1

        # Room (lobby by default)
        self._room = room
        self.set_room(room)

    def send(self, msgtype, data):
        send(self.sid, msgtype, data)

    def get_room(self):
        return self._room

    def set_room(self, roomname):
        with app.app_context():
            io.join_room(roomname, self.sid, "/")
        self._room = roomname

    def get_game(self):
        if self.get_room() != "lobby":
            return games[int(self.get_room().split("_")[1])]

@app.route("/")
def index():
    return flask.send_file("./public/index.html")

@app.route("/<path:path>")
def sendfile(path):
    return flask.send_from_directory("public", path)

# Websocket functionality
@sock.on("msg")
def recieve(message):
    "Recieve a message from a client"
    player = players[flask.request.sid]
    data = unpack(message)
    info = data[1]
    if data[0] == msg.update:
        player.update(info[b"x"], info[b"y"], info[b"vx"], info[b"vy"])
    elif info == msg.login:
        pass # todo: login using GameJolt API

@sock.on("connect")
def connect():
    "New connected client"
    sid = flask.request.sid
    print("connection:", sid, flask.request.referrer)
    players[sid] = player = Player(sid, 2, 8, "lobby")
    player.send(msg.init, {"sid": sid})
    waitqueue.append(player)

@sock.on("disconnect")
def disconnect():
    "Client disconnected"
    player = players[flask.request.sid]
    print("disconnection:", player.sid, flask.request.referrer)
    if player.get_room() != "lobby":
        # Remove player from their game
        player.get_game().removeplayer(player)
        io.leave_room(player.get_room())
    else:
        # Remove player from waitqueue
        waitqueue.remove(player)
        io.leave_room("lobby")
    players.pop(player.sid)

def gameloop():
    "The main game loop"
    dtick = 0
    print("started gameloop")
    while True:
        # Start timer
        dtick = time.clock()

        # Update games
        for game in games:
            game.update()

        # Update game queue
        for player in waitqueue:
            if len(games) <= maxgames:
                if len(games) == 0 or games[-1].started:
                    games.append(Game())
                games[-1].addplayer(player)
                waitqueue.remove(player)
                break

        # Wait delta time
        dtick = time.clock() - dtick
        if dtick < server["ticktime"]: sock.sleep(server["ticktime"] - dtick)

if __name__ == "__main__":
    print("starting...")
    gamethread = sock.start_background_task(gameloop)
    sock.run(app, host="0.0.0.0", port=8080)
