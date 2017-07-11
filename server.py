import time
from enum import IntEnum as enum
import flask
import flask_socketio as io
import msgpack

# Helper functions
def pack(obj):
	"Packs any object using msgpack"
	return msgpack.packb(obj)

def unpack(msg):
	"Unpacks a websocket message"
	return msgpack.unpackb(bytearray(msg["data"]))

def send(recipient, msgtype, data):
	"Sends a message (to a room or a single client's SID)"
	sock.emit("msg", {"data": pack([msgtype, data])}, room=recipient)

# Setup server app
app = flask.Flask(__name__, static_url_path="/public")
app.config["SERVER_NAME"] = "0.0.0.0:8080"

# Setup websocket app
players = {}
sock = io.SocketIO(app)

# Setup game globals
game = {"ticktime": 1/20}
msg = enum("msg", "join leave game pos login init")

# Game structures
class Player(object):
	def __init__(self, sid, x, y, room="lobby"):
		self.sid = sid
		self.x = x
		self.y = y
		self.room = room
	
	def update(self, x, y):
		self.x = x
		self.y = y
	
	def send(self, msgtype, data):
		send(self.sid, msgtype, data)

# Static file serving
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
	if data[0] == msg.pos:
		player.update(info[b"x"], info[b"y"])
	elif info == msg.login:
		pass # todo: login using GameJolt API

@sock.on("connect")
def connect():
	"New connected client"
	sid = flask.request.sid
	print("connection:", sid, flask.request.referrer)
	io.join_room("lobby")
	players[sid] = player = Player(0, 0, "lobby")
	send("lobby", msg.join, "player joined")
	player.send(msg.init, {"sid": sid})

@sock.on("disconnect")
def disconnect():
	"Client disconnected"
	print("disconnection:", flask.request.sid, flask.request.referrer)
	send("lobby", msg.leave, "player left")
	io.leave_room(players[flask.request.sid].room)
	players.pop(flask.request.sid)

def gameloop():
	"The main game loop"
	dtick = 0
	print("started gameloop")
	while True:
		# Start timer
		dtick = time.clock()
		
		# Game loop
		send("lobby", msg.game, "info")

		# Wait delta time
		dtick = time.clock() - dtick
		if dtick < game["ticktime"]: sock.sleep(game["ticktime"] - dtick)

if __name__ == "__main__":
	print("starting...")
	gamethread = sock.start_background_task(gameloop)
	sock.run(app)