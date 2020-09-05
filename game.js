"use strict";

var VERSION = "1.0.3";

/* globals $, msgpack, sprintf, io, pako */

var keyboard = {
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
		home: 65,
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
	input.anykey = true;
});
$(document).keyup(function (event) {
	keyboard.keys[keyboard.keymap[event.key.toLowerCase()]] = 0;
});
$(window).resize(function () {
	if (game.status != "loading") cam.zoom();
});
var touch = {
	right: false,
	righthold: false,
	left: false,
	lefthold: false,
	last: -1,
	time: 0,
	timer: null
};
var input = {
	jump: function () {
		return keyboard.down("space", "w", "up") || touch.right || touch.left;
	},
	right: function () {
		return keyboard.down("right", "d") || touch.righthold;
	},
	left: function () {
		return keyboard.down("left", "a") || touch.lefthold;
	},
	anykey: false
};
$(document).on("touchstart", function (event) {
	if (touch.righthold || touch.lefthold) {
		touch.right = true;
	}
	var x = event.touches[0].clientX;
	var y = event.touches[0].clientY;
	if ((cam.rot && y > window.innerWidth / 2) ||
		(!cam.rot && x > window.innerWidth / 2)) touch.righthold = true;
	else touch.lefthold = true;
});
$(document).on("touchend", function (event) {
	if (event.touches.length == 0) {
		touch.righthold = false;
		touch.lefthold = false;
	}
});
$(document).on("touchmove", function () {
	touch.righthold = touch.lefthold = false;
	var x = event.clientX;
	var y = event.clientY;
	if ((cam.rot && y > window.innerWidth / 2) ||
		(!cam.rot && x > window.innerWidth / 2))
		touch.righthold = true;
	else
		touch.lefthold = true;
});

var AUTO_LANDSCAPE = false;
var address = location.href.search("localhost") == -1 ? "52.9.158.129:8080" : location.href;
console.log("connecting to " + address);
var sock = io.connect(address);
var sp = sprintf;
var body = $(document.body);
var gbody = $("#game");
var $msg = $("#msg");
var login = $("#login");
var loginface = $("#login .player");
var infoelem = $("#i");
var leaderboard = $(".leaderboard");
var leaderbplace = $(".leaderboard p#placement");
var lbtable = $(".leaderboard tbody");
var $info = $("#linfo");
var $slead = $("#sml-leaderboard");
var $lobbyinfo = $("#login-msg");
var BOTTOM = 1;
var TOP = 2;
var LEFT = 4;
var RIGHT = 8;
var eyes = [":", ";", "8", "B"];
var mouths = ["}", "]", ")", "(", "[", "{", "|", "\\", ">", "&", "L", "I", "D", "3", "1", "P", "B", "S"];
var msg = {
	join: 1,
	leave: 2,
	game: 3,
	update: 4,
	login: 5,
	init: 6,
	endgame: 7,
	win: 8,
	dead: 9,
	info: 10,
	leaderboard: 11,
	lobbyinfo: 12
};


function dropdown(message) {
	$msg.text(message);
	$msg.removeClass("dropdown");
	setTimeout(function () {
		$msg.addClass("dropdown")
	}, 100);
}

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

function dist(x1, y1, x2, y2) {
	return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
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
			player.friction = info.drag;
			player.gravity = info.gravity;
			player.jumpspeed = info.vspeed;
			player.speed = info.hspeed;
			cam.target = player;
			game.setstatus("login");
			break;
		case msg.info:
			var infotext = info.split(";").join("<br>");
			$info.html(infotext);
			break;
		case msg.game:
			console.log("game %d started", info.number);
			game.setstatus("game");
			stage.create(info.data);
			for (var i = 0; i < info.players.length; i++) {
				if (info.players[i].gid != player.gid) new Actor(
					"friend", 0, 0, 65, 65,
					info.players[i].name, "", info.players[i].gid);
			}
			break;
		case msg.update:
			//Update actors from server
			for (var i = 0; i < info.gid.length; i++) {
				if (info.gid[i] == player.gid) continue;
				actor = stage.actors[stage.findByIndex(info.gid[i])];
				if (!actor || actor.halt) continue;
				actor.px = actor.nx;
				actor.py = actor.ny;
				actor.nx = info.x[i];
				actor.ny = info.y[i];
				actor.itime = (Date.now() / 1000) - actor.lastupdate
				actor.lastupdate = Date.now() / 1000
				actor.pvx = actor.nvx;
				actor.pvy = actor.nvy;
				actor.nvx = info.vx[i];
				actor.nvy = info.vy[i];
			}
			ActorMaxInterp = ActorCountInterp;
			ActorCountInterp = 0;
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
			if (info.index != player.gid) stage.removeByIndex(info.index);
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
				case -1:
					leaderbplace.text("Did Not Finish");
					audio.lose.play()
					break;
				case 1:
					leaderbplace.text("1st Place!");
					leaderbplace.addClass("winner");
					audio.bigwin.play()
					break;
				case 2:
					leaderbplace.text("2nd Place");
					audio.win.play()
					break;
				case 3:
					leaderbplace.text("3rd Place");
					audio.win.play()
					break;
				default:
					leaderbplace.text("Runner Up");
					break;
			}
			break;
		case msg.win:
			console.log("win: %.2f seconds", info.time / 20);
			break;
		case msg.login:
			console.log(info);
			dropdown(info);
			break;
		case msg.dead:
			if (info.gid == player.gid) break;
			actor = stage.actors[stage.findByIndex(info.gid)];
			actor.x = info.x + actor.vx * 2;
			actor.y = info.y + actor.vy * 2;
			actor.die();
			console.log("Recieved dead on player ", info.gid);
			break;
		case msg.leaderboard:
			$slead.html("<p>" + info.join("</p><p>") + "</p>");
			break;
		case msg.lobbyinfo:
			console.log(info);
			$lobbyinfo.html(info.split(";").join("<br>"));
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
			if (prop.type.search("spike") > -1) {
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
					prop.devare();
					this.props.splice(i, 1);
					return true;
				} else return false;
			}, this);
		}
	},
	create: function (data) {
		var minx = 0,
			miny = 0;
		var props = JSON.parse(data).props;
		for (var i = 0; i < props.length; i++) {
			new Prop(props[i].type,
				Math.floor(props[i].x),
				Math.floor(props[i].y),
				Math.floor(props[i].w),
				Math.floor(props[i].h));
			minx = Math.min(props[i].x, minx);
			miny = Math.min(props[i].y, miny);
		}
		minx -= 1000;
		miny -= 1000;
		this.bound(minx, miny);
	},
	findByIndex: function (gid) {
		return this.actors.findIndex(function (actor) {
			if (actor.gid == gid) return true;
			else return false;
		});
	},
	removeByIndex: function (gid) {
		var index = this.findByIndex(gid);
		if (index != -1) {
			this.actors[index].devare();
			this.actors.splice(index, 1);
		}
		else console.error("tried to remove actor #%d, but it doesn't exist", gid)
	},
	clear: function () {
		for (var i = this.props.length - 1; i >= 0; i--)
			this.props.pop().devare();
		for (var i = this.actors.length - 1; i >= 1; i--)
			this.actors.pop().devare();
	},
	bound: function (minx, miny) {
		gbody.css("left", -Math.min(0, minx) + "px");
		gbody.css("top", -Math.min(0, miny) + "px");
		cam.offsetx = -minx;
		cam.offsety = -miny;
	},
	timer: 0
};

var audio = (function () {
	var self = {};
	Array.from($("audio")).forEach(function (element) {
		this[element.id] = element;
	}, self);
	return self;
})();

var game = (function () {
	var self = {
		status: "loading",
		setstatus: function (status) {
			console.info(sp("STATUS: %s -> %s", this.status, status));

			// From status
			switch (this.status) {
				case "loading":
					$(".loading").hide();
					break;
				case "login":
					login.hide();
					$("#login-msg").hide();
					break;
				case "lobby":
					$("#title").hide();
					$(".loading").hide();
					break;
				case "game":
					infoelem.hide();
					gbody.hide();
					$slead.hide();
					break;
				case "endgame":
					leaderboard.hide();
					break;
				case "newgame":
					break;
				case "disconnected":
					$(".disconnected").hide();
					break;
			}
			this.status = status;

			// To status
			switch (status) {
				case "loading":
					cam.update();
					$(".loading").show();
					$(".disconnected").hide();
					break;
				case "login":
					$("#title").show();
					$("#login-msg").show();
					login.show();
					cam.target = null;
					cam.reset();
					break;
				case "lobby":
					$("#title").show();
					$(".loading").show();
					$(".disconnected").hide();
					stage.clear();
					break;
				case "game":
					infoelem.show();
					gbody.show();
					cam.target = player
					cam.zoom();
					cam.reset();
					$slead.empty();
					$slead.show();
					break;
				case "endgame":
					leaderboard.show();
					cam.target = null;
					cam.update();
					break;
				case "newgame":
					send(msg.game, 0);
					this.setstatus("lobby");
					break;
				case "disconnected":
					$(".disconnected").show();
					$("#title").hide();
					stage.clear();
					break;
			}
		}
	};
	return self;
})();

var cam = {
	x: 0,
	y: 0,
	offsetx: 0,
	offsety: 0,
	currFFZoom: 1,
	currIEZoom: 100,
	zoomlvl: 1,
	rot: false,
	target: null,
	speed: 0.1,
	update: function () {
		if (!this.target) {
			window.scrollTo(0, 0);
		} else {
			this.follow();
			if (!this.rot)
				window.scrollTo(this.offsetx + this.x, this.offsety + this.y);
			else
				window.scrollTo(this.offsety + this.y, this.offsetx + this.x);
		}
	},
	zoom: function () {
		var rotchange = this.rot;
		this.rot = (window.innerHeight / window.innerWidth) > 1;
		rotchange = (rotchange != this.rot);
		this.zoomlvl = ((window.innerWidth + window.innerHeight) / (1280 + 720)) + (this.rot ? 0.3 : 0);
		this.zoomlvl *= 0.7;
		this.zoomlvl.toFixed(1);
		gbody.css("transform", sp("scale(%1$f, %1$f)", this.zoomlvl));
		this.reset();
		if (rotchange && AUTO_LANDSCAPE) {
			if (this.rot) {
				body.addClass("landscape");
			} else {
				body.removeClass("landscape");
			}
		}
	},
	follow: function () {
		this.x = lerp(this.x, this.fx(), this.speed);
		this.y = lerp(this.y, this.fy(), this.speed);
	},
	reset: function () {
		if (this.target) {
			this.x = this.fx();
			this.y = this.fy();
		}
		if (game.status == "login") this.y *= 1.5;
		this.update();
	},
	fx: function () {
		return (this.target.x + this.target.w / 2) * this.zoomlvl - (
			(this.rot ? window.innerHeight : window.innerWidth) / 2);
	},
	fy: function () {
		return (this.target.y + this.target.h / 2) * this.zoomlvl - (
			(this.rot ? window.innerWidth : window.innerHeight) / 2);
	}
};
var ticks = 0;
var player = new Actor("player", 0, 0, 65, 65);
var ActorMaxInterp = 3
var ActorCountInterp = 0

//varructor Objects
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
		style: sp("left:%dpx;top:%dpx;width:%dpx;height:%dpx;",
			this.x, this.y, this.w, this.h),
		text: text || ""
	});
	gbody.append(dom);
	stage.addprop(this);

	//Methods
	this.devare = function () {
		dom.remove();
	};
}

function Actor(type, x, y, w, h, name, sid, gid) {
	//Properties
	this.name = name;
	this.x = x || 0;
	this.y = y || 0;
	this.w = w || 30;
	this.h = h || 30;
	this.vx = 0;
	this.vy = 0;
	this.dx = 0;
	this.dy = 0;
	this.pvx = 0;
	this.pvy = 0;
	this.nvx = 0;
	this.nvy = 0;
	this.px = 0;
	this.py = 0;
	this.nx = 0;
	this.ny = 0;
	this.npos = [0, 0]
	this.interp = 0;
	this.itime = 1;
	this.lastupdate = Date.now() / 1000;
	this.sid = sid || "";
	this.gid = gid || 0;
	this.face = ":)";
	this.type = type;
	this.speed = 6.5;
	this.jumpspeed = 18;
	this.gravity = 0.8;
	this.friction = 0.35;
	this.halt = false;

	//Initialize
	var dom = $("<div>", {
		class: type,
		style: sp("width:%dpx;height:%dpx;", w, h),
		text: this.face
	});
	gbody.append(dom);
	stage.actors.push(this);

	//Methods
	this.seedface = function (name) {
		this.name = name;
		Math.seedrandom(name);
		this.face = eyes[Math.floor(Math.random() * eyes.length)] +
			mouths[Math.floor(Math.random() * mouths.length)];
		dom.text(this.face);
		if (this.type == "friend") {
			dom.append($("<p>", {text: this.name}));
		}
	}
	this.move = function (dx, dy) {
		this.x += dx;
		this.y += dy;
		dom.css(
			"transform",
			sp(
				"translate(%dpx, %dpx) scale(%.2f, %.2f) rotate(%.2fdeg)",
				this.x, this.y,
				1 + Math.abs(this.dx / 75),
				1 + Math.abs(this.dy / 75),
				this.dx
			)
		);
	};
	this.update = function () {
		if (this.halt) return;	
		switch (this.type) {
			case "player":
				this.vx *= this.friction;
				if (input.right()) this.vx += this.speed;
				if (input.left()) this.vx -= this.speed;
				if (this.canjump && input.jump()) {
					this.vy = -this.jumpspeed;
					audio.jump.play();
					this.canjump = false;
				}
				this.vy += this.gravity;
				if (this.y > 99999) this.die();
				this.dx = this.vx;
				this.dy = this.vy;
				this.move(this.vx, this.vy);
				var spd = this.vy;
				var coll = collision(this);
				if (spd > 1.5 && this.vy === 0 && coll & BOTTOM) {
					audio.land.play();
				}
				if (coll & BOTTOM) {
					this.canjump = true;
				}
				break;
			case "friend":
				this.interp = Math.min(((Date.now() / 1000) - this.lastupdate) / this.itime, 1);
				this.vx = lerp(this.pvx, this.nvx, this.interp);
				this.vy = lerp(this.pvy, this.nvy, this.interp);
				this.x = lerp(this.px, this.nx, this.interp);
				this.y = lerp(this.py, this.ny, this.interp);
				this.dx = this.vx;
				this.dy = this.vy;
				this.move(0, 0);
				break;
		}
	};
	this.die = function () {
		this.x -= this.vx;
		this.y -= this.vy;
		new Prop("grave", this.x + 6, this.y - 10, 60, 80, this.face);
		new Effect(this.x + this.w / 2, this.y + this.h / 2, "4star.svg");
		this.vx = this.vy = 0;
		dom.addClass("padshrink");
		if (this.type == "player") {
			audio.die.play();
			send(msg.dead, {
				x: this.x,
				y: this.y
			});
			cam.speed = 0;
			this.suspend(false, 750, true);
		} else {
			this.suspend(false, 1000, true);
		}
	};
	this.win = function () {
		if (this.type != "player") return;
		this.vx = this.vy = 0;
		new Effect(this.x + this.w / 2, this.y + this.h / 2, "star.svg");
		send(msg.win, 0);
		audio.win.play();
		this.suspend(false, 750, true);
		dom.addClass("padshrink");
	};
	this.devare = function () {
		dom.remove();
	};
	this.hide = function () {
		dom.hide();
	};
	this.unhide = function () {
		dom.show();
	};
	this.suspend = function (hide, time, reset) {
		this.halt = true;
		if (hide) this.hide();
		var that = this;
		setTimeout(function () { that.unsuspend(reset); }, time);
	};
	this.unsuspend = function (reset) {
		if (reset) {
			this.x = stage.spawnx;
			this.y = stage.spawny;
			this.move(0, 0);
		}
		cam.speed = 0.1;
		this.halt = false;
		this.unhide();
		dom.removeClass("padshrink");
	};

	if (name) this.seedface(name);
}

function Effect(x, y, image) {
	var dom = $("<img>", {
		class: "spinfect",
		src: "../img/" + image,
		style: sp("top:%dpx; left:%dpx;", y - 100, x - 100)
	});
	gbody.append(dom);

	this.devare = function () {
		dom.remove();
	};
	setTimeout(this.devare, 2000);
}

function gameloop() {
	window.requestAnimationFrame(gameloop);
	ticks++;

	switch (game.status) {
		case "game":
			if (stage) {
				stage.update();
				ActorCountInterp += 1;
			}
			cam.update();
			if (ticks % 3 == 0) send(msg.update, {
				x: player.x,
				y: player.y,
				vx: player.vx,
				vy: player.vy
			});
			break;
		case "login":
			if (input.anykey) {
				player.seedface(login.find("input").val());
				loginface.text(player.face);
			}
			if (keyboard.pressed("home")) {
				send(msg.login, "player");
			}
			break;
	}

	//Reset input
	for (var i = 0; i < 128; keyboard.keyspressed[i] = 0, i++);
	touch.right = false;
	touch.left = false;
	input.anykey = false;
}

game.setstatus("loading");
cam.zoom();
audio.music.play();
window.requestAnimationFrame(gameloop);

$("#version").append(VERSION);

//GameJolt usage
if (GJAPI.bOnGJ && GJAPI.bActive) {
	console.log("GameJolt logged in!");
	$("#login form input").val(GJAPI.sUserName);
	$("#login form input").attr("readonly", "readonly");
	$("#login form input").css("background-color", "#3C4C4F");
	$("#version").append(" GJ " + GJAPI.sUserName + " " + GJAPI.sUserToken);
}

player.seedface(login.find("input").val());
loginface.text(player.face);

window["_g_login"] = function (name) {
	send(msg.login, [name, GJAPI.sUserToken]);
};
window["_g_status"] = function (status) {
	game.setstatus(status)
};