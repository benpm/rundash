from math import floor

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

        # Consecutive wins
        self.wins = 0
    
    def reset_game_state(self):
        self.gindex = -1
        self.game = None
        self.win = None
        self.timer = 0
    def death(self):
        self.timer = 0
        self.game.sendplayerdeath(self)

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