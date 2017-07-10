import os
import flask
import flask_socketio as ws
print(__name__)
wdir = os.getcwd()
app = flask.Flask(__name__, static_url_path="/public")
app.config["SECRET_KEY"] = "..."
sock = ws.SocketIO(app)

@app.route("/")
def index():
    return flask.send_file("./public/index.html")

@app.route('/<path:path>')
def sendfile(path):
    return flask.send_from_directory('public', path)

@sock.on("message")
def recieve():
    print("recieved information")

@sock.on("connect")
def connect():
    sock.emit("my response", {"data": "Connected"})

@sock.on("disconnect")
def disconnect():
    print("Client disconnected")

if __name__ == "__main__":
	print(app.config.keys())
	sock.run(app)