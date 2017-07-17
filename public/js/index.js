/* globals $, msgpack, sprintf, io, pako */

const keyboard = {
	keymap: {
		" ": 32,
		space: 32,
		spacebar: 32,
		control: 33,
		shift: 34,
		alt: 35,
		tab: 36,
		return: 37,
		enter: 38,
		lshift: 39,
		arrowleft: 40,
		left: 40,
		arrowright: 41,
		right: 41,
		arrowup: 42,
		up: 42,
		arrowdown: 43,
		down: 43,
		",": 44,
		"-": 45,
		".": 46,
		"/": 47,
		"0": 48,
		"1": 49,
		"2": 50,
		"3": 51,
		"4": 52,
		"5": 53,
		"6": 54,
		"7": 55,
		"8": 56,
		"9": 57,
		":": 58,
		";": 59,
		"<": 60,
		"=": 61,
		">": 62,
		"?": 63,
		"@": 64,
		A: 65,
		B: 66,
		C: 67,
		D: 68,
		E: 69,
		F: 70,
		G: 71,
		H: 72,
		I: 73,
		J: 74,
		K: 75,
		L: 76,
		M: 77,
		N: 78,
		O: 79,
		P: 80,
		Q: 81,
		R: 82,
		S: 83,
		T: 84,
		U: 85,
		V: 86,
		W: 87,
		X: 88,
		Y: 89,
		Z: 90,
		"[": 91,
		"": 92,
		"]": 93,
		"^": 94,
		F1: 95,
		"`": 96,
		a: 97,
		b: 98,
		c: 99,
		d: 100,
		e: 101,
		f: 102,
		g: 103,
		h: 104,
		i: 105,
		j: 106,
		k: 107,
		l: 108,
		m: 109,
		n: 110,
		o: 111,
		p: 112,
		q: 113,
		r: 114,
		s: 115,
		t: 116,
		u: 117,
		v: 118,
		w: 119,
		x: 120,
		y: 121,
		z: 122,
		"{": 123,
		"|": 124,
		"}": 125,
		"~": 126
	},
	keys: new Uint8Array(128),
	keyspressed: new Uint8Array(128),
	down: function () {
		return !!Array.from(arguments).find(function (key) {
			return keyboard.keys[keyboard.keymap[key]] == 1;
		});
	},
	pressed: function () {
		return !!Array.from(arguments).find(function (key) {
			return keyboard.keyspressed[keyboard.keymap[key]] == 1;
		});
	}
};
$(document).keydown(function (event) {
	keyboard.keys[keyboard.keymap[event.key.toLowerCase()]] = 1;
	keyboard.keyspressed[keyboard.keymap[event.key.toLowerCase()]] = 1;
});
$(document).keyup(function (event) {
	keyboard.keys[keyboard.keymap[event.key.toLowerCase()]] = 0;
});
$(window).resize(function () {
	cam.zoom();
});
const touch = {
	right: false,
	righthold: false,
	left: false,
	lefthold: false,
	last: -1,
	time: 0,
	timer: null
};
const input = {
	jump: function () {
		return keyboard.down("space", "w", "up") || touch.right || touch.left;
	},
	right: function () {
		return keyboard.down("right", "d") || touch.righthold;
	},
	left: function () {
		return keyboard.down("left", "a") || touch.lefthold;
	}
};
$(document).on("touchstart", function (event) {
	if (touch.righthold || touch.lefthold) {
		touch.right = true;
	}
	var x = event.touches[0].clientX;
	var y = event.touches[0].clientY;
	if ((cam.rot && y > window.innerWidth / 2)
		|| (!cam.rot && x > window.innerWidth / 2)) touch.righthold = true;
	else touch.lefthold = true;
});
$(document).on("touchend", function (event) {
	if (event.touches.length == 0) {
		touch.righthold = false;
		touch.lefthold = false;
	}
});
$(document).on("touchmove", function () {
	console.log("move");
});

const address = location.href;
const sock = io.connect(address);
const sp = sprintf;
const gbody = $("#game");
const login = $("#login");
const infoelem = $("#i");
const leaderboard = $(".leaderboard");
const leaderbplace = $(".leaderboard p#placement");
const lbtable = $(".leaderboard tbody");
const BOTTOM = 1;
const TOP = 2;
const LEFT = 4;
const RIGHT = 8;
const msg = {
	join: 1,
	leave: 2,
	game: 3,
	update: 4,
	login: 5,
	init: 6,
	endgame: 7,
	win: 8,
	dead: 9
};

function cubicHermite(p0, v0, p1, v1, t, f) {
	var ti = (t - 1),
		t2 = t * t,
		ti2 = ti * ti,
		h00 = (1 + 2 * t) * ti2,
		h10 = t * ti2,
		h01 = t2 * (3 - 2 * t),
		h11 = t2 * ti
	if (p0.length) {
		if (!f) {
			f = new Array(p0.length)
		}
		for (var i = p0.length - 1; i >= 0; --i) {
			f[i] = h00 * p0[i] + h10 * v0[i] + h01 * p1[i] + h11 * v1[i]
		}
		return f
	}
	return h00 * p0 + h10 * v0 + h01 * p1 + h11 * v1
}

function decode(msg) {
	return msgpack.decode(new Uint8Array(msg.data));
}

function send(msgtype, msg) {
	if (sock.connected)
		sock.emit("msg", msgpack.encode([msgtype, msg]));
}

sock.on("connect", function () {
	console.log(sp("connected to %s", sock.io.uri));
	game.setstatus("loading");
});

sock.on("msg", function (message) {
	var actor, placement;
	var data = decode(message);
	var info = data[1];
	switch (data[0]) {
		case msg.init:
			console.log("initialized");
			player.sid = info.sid;
			cam.target = player;
			game.setstatus("login");
			break;
		case msg.game:
			console.log("game %d started", info.number);
			game.setstatus("game");
			stage.create(info.data);
			for (var i = 0; i < info.players; i++) {
				if (i != player.gid) new Actor("friend", 2, 8, 3, 3, ":|", "", i);
			}
			break;
		case msg.update:
			for (var i = 0; i < info.gid.length; i++) {
				if (info.gid[i] == player.gid) continue;
				actor = stage.actors[stage.findByIndex(info.gid[i])];
				if (!actor) continue;
				actor.interp = 0;
				actor.nx = info.x[i];
				actor.ny = info.y[i];
				actor.nvx = info.vx[i];
				actor.nvy = info.vy[i];
			}
			infoelem.text(sp("%d seconds left", info.time));
			break;
		case msg.join:
			console.log("joined game %d", info.number);
			game.setstatus("lobby");
			player.gid = info.gid;
			stage.spawnx = player.x = info.x;
			stage.spawny = player.y = info.y;
			break;
		case msg.leave:
			console.log("player %d left", info.index);
			stage.removeByIndex(info.index);
			break;
		case msg.endgame:
			console.log("game ended");
			game.setstatus("endgame");

			//Assemble leaderboard
			$(".leaderboard tr").remove("tr:not(#header)");
			placement = -1
			for (var i = 0, row, dnf; i < info.length; i++) {
				dnf = !Boolean(info[i].time);
				if (info[i].sid == player.sid && !dnf) placement = i + 1;
				lbtable.append(row = $("<tr>", {
					class: (info[i].sid == player.sid ? "me " : "") + (dnf ? "dnf" : "")
				}));
				row.append($("<td>", {
					text: dnf ? "" : (i + 1).toString()
				}));
				row.append($("<td>", {
					text: info[i].name
				}));
				row.append($("<td>", {
					text: dnf ? "DNF" : (info[i].time / 20).toFixed(1) + " sec"
				}));
			}

			//Create placement text
			leaderbplace.removeClass("winner");
			switch (placement) {
				case -1: leaderbplace.text("Did Not Finish"); break;
				case 1:
					leaderbplace.text("1st Place!");
					leaderbplace.addClass("winner");
					break;
				case 2: leaderbplace.text("2nd Place"); break;
				case 3: leaderbplace.text("3rd Place"); break;
				default: leaderbplace.text("Runner Up"); break;
			}
			break;
		case msg.win:
			console.log("win: %.2f seconds", info.time / 20);
			break;
	}
});

sock.on("disconnect", function () {
	console.log("disconnected from server");
	game.setstatus("disconnected");
});

function lerp(v0, v1, t) {
	return (1 - t) * v0 + t * v1;
}

function collision(actor) {
	var collide = 0;
	stage.props.forEach(function (prop) {
		if (
			prop.solid &&
			actor.y + actor.h >= prop.y &&
			actor.y <= prop.y + prop.h &&
			actor.x + actor.w >= prop.x &&
			actor.x <= prop.x + prop.w
		) {
			if (prop.type == "spike") {
				actor.die();
				return;
			}
			if (prop.type == "platform goal") {
				actor.win();
				return;
			}
			var dy1 = actor.y + actor.h - prop.y;
			var dy2 = prop.y + prop.h - actor.y;
			var dx1 = actor.x + actor.w - prop.x;
			var dx2 = prop.x + prop.w - actor.x;
			var c = Math.min(
				Math.abs(dy1),
				Math.abs(dy2),
				Math.abs(dx1),
				Math.abs(dx2)
			);
			if (c == dy1) {
				actor.y = prop.y - actor.h;
				actor.vy = 0;
				collide |= BOTTOM;
			} else if (c == dy2) {
				actor.y = prop.y + prop.h;
				actor.vy = -actor.vy / 2 + 0.1;
				collide |= TOP;
			} else if (c == dx1) {
				actor.x = prop.x - actor.w;
				collide |= RIGHT;
			} else if (c == dx2) {
				actor.x = prop.x + prop.w;
				collide |= LEFT;
			}
			actor.move(0, 0);
		}
	});
	return collide;
}

function uintToString(uintArray) {
	var encodedString = String.fromCharCode.apply(null, uintArray),
		decodedString = decodeURIComponent(escape(encodedString));
	return decodedString;
}

var stage = {
	maxprops: 180,
	props: [],
	actors: [],
	spawnx: 0,
	spawny: 0,
	update: function () {
		for (var i = 0; i < this.actors.length; i++) {
			this.actors[i].update();
		}
		this.timer++;
	},
	addprop: function (prop) {
		this.props.push(prop);
		if (this.props.length > this.maxprops) {
			this.props.find(function (prop, i) {
				if (prop.type == "grave") {
					prop.delete();
					this.props.splice(i, 1);
					return true;
				} else return false;
			}, this);
		}
	},
	create: function (data) {
		/* var y = 16;
		for (var i = 0; i < 16; i++) {
			y = Math.round(y + (Math.random() - 0.5) * 8);
			var w = Math.round(4 + Math.random() * 4) * 2;
			new Prop("platform", i * 16, y, w, 2);
			if (i == 15) new Prop("platform goal", i * 16 + w + 2, y - 8, 2, 8);
			if (Math.random() < 0.5 && i > 1) new Prop("spike", i * 16 + 4, y - 2, Math.round(w / 6) * 2);
		}
		new Prop("spike", 2, 44, 302, 2);
		new Prop("platform", 0, 0, 2, 48);
		new Prop("platform", -2, 46, 302, 2); */
		/* new Prop("platform", -10, 16, 20, 8);
		var str = pako.inflate(data, {to: "string"});
		console.log(str); */
		var props = JSON.parse(data).props;
		for (var i = 0; i < props.length; i++) {
			new Prop(props[i].type,
				props[i].x,
				props[i].y,
				props[i].w,
				props[i].h);
		}
	},
	findByIndex: function (gid) {
		return this.actors.findIndex(function (actor) {
			if (actor.gid == gid) return true;
			else return false;
		});
	},
	removeByIndex: function (gid) {
		const index = this.findByIndex(gid);
		if (index != -1) this.actors.splice(index, 1);
		else console.error("tried to remove actor #%d, but it doesn't exist", gid)
	},
	clear: function () {
		for (var i = this.props.length - 1; i >= 0; i--)
			this.props.pop().delete();
		for (var i = this.actors.length - 1; i >= 1; i--)
			this.actors.pop().delete();
	},
	timer: 0
};

const audio = (function () {
	var self = {};
	Array.from($("audio")).forEach(function (element) {
		this[element.id] = element;
	}, self);
	return self;
})();

const game = (function () {
	var self = {
		status: "loading",
		setstatus: function (status) {
			console.info(sp("STATUS: %s -> %s", this.status, status));
			this.status = status;
			switch (status) {
				case "loading":
					$(".loading").show();
					$(".disconnected").hide();
					leaderboard.hide();
					gbody.hide()
					break;
				case "login":
					cam.zoom();
					$(".loading").hide();
					$(".disconnected").hide();
					login.show();
					break;	
				case "lobby":
					$(".loading").show();
					$(".disconnected").hide();
					login.hide();
					infoelem.hide();
					gbody.hide();
					stage.clear();
					leaderboard.hide();
					break;
				case "game":
					$(".loading").hide();
					$(".disconnected").hide();
					infoelem.show();
					gbody.show();
					cam.zoom();
					cam.reset();
					break;
				case "endgame":
					$(".disconnected").hide();
					infoelem.hide();
					gbody.hide();
					leaderboard.show();
					break;
				case "newgame":
					send(msg.game, 0);
					this.setstatus("lobby");
					break;
				case "disconnected":
					$(".loading").hide();
					$(".disconnected").show();
					gbody.hide();
					infoelem.hide();
					leaderboard.hide();
					stage.clear();
					break;
			}
		}
	};
	return self;
})();

const cam = {
	x: 0,
	y: 0,
	currFFZoom: 1,
	currIEZoom: 100,
	zoomlvl: 1,
	rot: false,
	target: null,
	speed: 0.1,
	update: function () {
		if (this.target) this.follow();
		gbody.css(
			"transform",
			sp(
				"%s scale(%.2f, %.2f) translate(%.2fpc, %.2fpc)",
				this.rot ? "rotate(90deg)" : "",
				this.zoomlvl,
				this.zoomlvl,
				this.rot ? -this.x - ((window.innerWidth / this.zoomlvl) / 32) +
				((window.innerHeight / this.zoomlvl) / 32) : -this.x,
				this.rot ? -this.y - ((window.innerHeight / this.zoomlvl) / 32) -
				((window.innerWidth / this.zoomlvl) / 32) : -this.y
			)
		);
	},
	zoom: function () {
		var rotchange = this.rot;
		this.rot = (window.innerHeight / window.innerWidth) > 1;
		rotchange = (rotchange != this.rot);
		this.zoomlvl = ((window.innerWidth + window.innerHeight) / (1280 + 720)) + (this.rot ? 0.3 : 0);
		this.reset();
		if (rotchange) {
			if (this.rot) {
				leaderboard.addClass("landscape");
				infoelem.addClass("landscape");
				login.addClass("landscape");
			} else {
				leaderboard.removeClass("landscape");
				infoelem.removeClass("landscape");
				login.removeClass("landscape");
			}
		}
	},
	follow: function () {
		this.x = lerp(this.x, this.fx(), this.speed);
		this.y = lerp(this.y, this.fy(), this.speed);
	},
	reset: function () {
		this.x = this.fx();
		this.y = this.fy();
	},
	fx: function () {
		return this.target.x + this.target.w / 2 - ((window.innerWidth / this.zoomlvl) / 32);
	},
	fy: function () {
		return this.target.y + this.target.h / 2 - ((window.innerHeight / this.zoomlvl) / 32);
	}
};
var ticks = 0;
var player = new Actor("player", 2, 8, 3, 3, ":)");

//Constructor Objects
function Prop(type, x, y, w, h, text) {
	//Properties
	this.type = type;
	this.x = x || 0;
	this.y = y || 0;
	this.w = w || 2;
	this.h = h || 2;
	this.solid = type == "grave" ? false : true;

	//Initialize
	var dom = $("<div>", {
		class: type,
		style: sp("left:%dpc;top:%dpc;width:%dpc;height:%dpc;",
			this.x, this.y, this.w, this.h),
		text: text || ""
	});
	gbody.append(dom);
	stage.addprop(this);

	//Methods
	this.delete = function () {
		dom.remove();
	};
}

function Actor(type, x, y, w, h, face, sid, gid) {
	//Properties
	this.x = x || 0;
	this.y = y || 0;
	this.w = w || 2;
	this.h = h || 2;
	this.vx = 0;
	this.vy = 0;
	this.dx = 0;
	this.dy = 0;
	this.nx = 0;
	this.ny = 0;
	this.nvx = 0;
	this.nvy = 0;
	this.npos = [0, 0]
	this.interp = 0;
	this.sid = sid || "";
	this.gid = gid || 0;
	this.face = face || ":|";
	this.type = type;

	//Initialize
	var dom = $("<div>", {
		class: type,
		style: sp("width:%dpc;height:%dpc;", w, h),
		text: face
	});
	gbody.append(dom);
	stage.actors.push(this);

	//Methods
	this.move = function (dx, dy) {
		this.x += dx;
		this.y += dy;
		dom.css(
			"transform",
			sp(
				"translate(%.2fpc, %.2fpc) scale(%.2f, %.2f) rotate(%.2fdeg)",
				this.x, this.y,
				1 + Math.abs(this.dx / 3),
				1 + Math.abs(this.dy / 3),
				90 + this.dx * 15
			)
		);
	};
	this.update = function () {
		switch (this.type) {
			case "player":
				this.vx /= 2;
				if (input.right()) this.vx += 0.25;
				if (input.left()) this.vx -= 0.25;
				if (this.canjump && input.jump()) {
					this.vy = -0.72;
					audio.jump.play();
					this.canjump = false;
				}
				this.vy += 0.04;
				if (this.y > 64) this.die();
				this.dx = this.vx;
				this.dy = this.vy;
				this.move(this.vx, this.vy);
				var spd = this.vy;
				var coll = collision(this);
				if (spd > 0.1 && this.vy === 0 && coll & BOTTOM) {
					audio.land.play();
				}
				if (coll & BOTTOM) {
					this.canjump = true;
				}
				break;
			case "friend":
				this.interp += (1 - this.interp) / 3;
				cubicHermite(
					[this.x, this.y], [this.vx, this.vy], [this.nx, this.ny], [this.nvx, this.nvy],
					this.interp, this.npos
				)
				this.dx = lerp(this.dx, this.npos[0] - this.x, 0.5);
				this.dy = lerp(this.dy, this.npos[1] - this.y, 0.5);
				this.dx = Math.abs(this.dx) > 1.5 ? 0 : this.dx;
				this.dy = Math.abs(this.dy) > 1.5 ? 0 : this.dy;
				this.x = this.npos[0];
				this.y = this.npos[1];
				this.move(0, 0);
				break;
		}
	};
	this.die = function () {
		if (this.type == "player") send(msg.dead, { x: this.x, y: this.y });
		new Prop("grave", this.x - this.vx, this.y - this.vy, 4, 3, ":(");
		this.vx = this.vy = 0;
		this.x = 2;
		this.y = 6;
		this.move(0, 0);
		audio.die.play();
	};
	this.win = function () {
		if (this.type != "player") return;
		this.vx = this.vy = 0;
		this.x = 2;
		this.y = 6;
		this.move(0, 0);
		send(msg.win, 0);
		audio.win.play();
	};
	this.delete = function () {
		dom.remove();
	};
}

function gameloop() {
	window.requestAnimationFrame(gameloop);
	ticks++;
	//info.html(sp("%s, %s", game.status, sock.connected ? "connected" : "not connected"));

	switch (game.status) {
		case "game":
			if (stage) stage.update();
			cam.update();
			if (ticks % 3 == 0) send(msg.update, {
				x: player.x,
				y: player.y,
				vx: player.vx,
				vy: player.vy
			});
			break;
	}

	//Reset input
	for (var i = 0; i < 128; keyboard.keyspressed[i] = 0, i++);
	touch.right = false;
	touch.left = false;
}

game.setstatus("loading");
window.requestAnimationFrame(gameloop);