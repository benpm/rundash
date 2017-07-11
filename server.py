import time
from enum import IntEnum as enum
import flask
import flask_socketio as io
import msgpack

def pack(obj):
	return msgpack.packb(obj)
def unpack(msg):
	return msgpack.unpackb(bytearray(msg["data"]))
def send(recipient, msgtype, data):
	sock.emit("msg", {"data": pack([msgtype, data])}, room=recipient)

app = flask.Flask(__name__, static_url_path="/public")
app.config["SECRET_KEY"] = "..."
app.config["SERVER_NAME"] = "127.0.0.1:8080"
sock = io.SocketIO(app)
game = {"ticktime": 1/20}
clients = []
msg = enum("msg", "join leave game")
print(msg)

@app.route("/")
def index():
	return flask.send_file("./public/index.html")

@app.route("/<path:path>")
def sendfile(path):
	return flask.send_from_directory("public", path)

@sock.on("msg")
def recieve_hello(msg):
	print("NET: recieved", unpack(msg))

@sock.on("connect")
def connect():
	print("connection:", flask.request.sid, flask.request.referrer)
	io.join_room("lobby")
	clients.append(flask.request.sid)
	send("lobby", msg.join, "player joined")
	send(flask.request.sid, msg.join, flask.request.sid)

@sock.on("disconnect")
def disconnect():
	print("disconnection:", flask.request.sid, flask.request.referrer)
	send("lobby", msg.join, "player left")
	clients.remove(flask.request.sid)
	io.leave_room("lobby")

def gameloop():
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
	#netthread = threading.Thread(name="net", target=sock.run, args=(app,))
	#netthread.start()
	gamethread = sock.start_background_task(gameloop)
	sock.run(app)

	#print("mmm")
	#gameloop(True)