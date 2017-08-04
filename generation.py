from math import *
import random
import msgpack
import gzip
import json

def build_level(type_, grid = 10):
    return Level(type_, grid)

class Level(object):
    GRID = 10
    def __init__(self, type_, grid = 10, maxh = 300, maxv = 200):
        self.GRID = grid
        self.maxh = maxh / grid
        self.maxv = maxv / grid

        self.spawnx = 0
        self.spawny = 7

        self.props = []

        if type_ is "horizontal":
            self.generate_horizontal()
        elif type_ is "vertical":
            self.generate_vertical()
        elif type_ is "classic":
            self.generate_classic()

    def generate_classic(self):
        x = -7
        y = 10
        w = 20
        h = 4
        difficulty = 5
        n = None
        newtype = ""

        # Starting platform
        self.insert(Prop(x, y, w, h, "platform"))
        x += w + 5

        # Varying ingredients
        for i in range(20):
            newtype = random.choices(["horizontal", "stairs", "wall"], [100, 10, 5])[0]
            if newtype == "horizontal":
                n = IHorizontal(x, y, difficulty, 15, 40)
            elif newtype == "stairs":
                n = IStairs(x, y, difficulty,
                            random.randint(5, 10), 8, random.randint(-16, -4))
            elif newtype == "wall":
                n = IWall(x, y, difficulty, self.maxh - 1)
            n.place(self)
            x = n.x2 + random.randint(10, self.maxh)
            y = n.y2 + random.randint(-self.maxv, self.maxv * 2)

        # Goal
        self.goal = Prop(x + 10, y - 20, 4, 30, "platform goal")
        self.insert(self.goal)

        # Compress
        self.compress()

    def generate_horizontal(self):
        # Prop (x, y, w, h, proptype)
        # Prop types: "platform", "goal", "spike"
        max_x = 36
        min_x = 10

        max_y_up = 8
        max_y_down = 10
        min_y = 0

        x = -7
        y = 10
        w = 20
        h = 4

        # Starting platform
        self.insert(Prop(x, y, w, h, "platform"))

        # Spike floor
        self.insert(Prop(-1000, 110, 2000, h, "platform"))
        self.insert(Prop(-1000, 110 - 5, 2000, 5, "spike"))

        num_platforms = random.randint(7, 15)
        for i in range(0, num_platforms):
            plat_vert_sign = random.choice([1, -1, -1])

            delta_x = random.uniform(min_x, max_x)
            norm_x = self.normalize(delta_x, max_x, min_x)

            if plat_vert_sign == 1:
                # Going down allows for larger drop
                delta_y = (1.9 - norm_x) * random.uniform(8, 10)
            else:
                delta_y = (1.12 - norm_x) * random.uniform(8, 10)

            delta_y *= plat_vert_sign
            prev_dist = self.distance(x + w, y + w, x + delta_x, y + delta_y)

            x += delta_x + w
            y += delta_y

            w = random.uniform(10, 30)

            self.insert(Prop(x, y, w, h, "platform"))

            # Need to base spike probability on normalized values
            if norm_x < 0.9 and plat_vert_sign == 1 and random.random() < .7:
                self.insert(
                    Prop(x, y - 5, 5, 5, "spike"))
            elif w > 12 and random.random() < 0.6:
                self.insert(
                    Prop(
                        x + random.randrange(0 if (plat_vert_sign == 1) else 2, round(w / 2), 5) + random.random(),
                        y - 5,
                        5,
                        5,
                        "spike"))
            if w > 25 and random.random() < 0.5:
                self.insert(
                    Prop(
                        x + random.randrange(round(w / 2) + 2 if plat_vert_sign is 1 else 0 , round(w * .8), 5),
                        y - 5,
                        5,
                        5,
                        "spike"))

        # Goal
        self.goal = Prop(x + 30 + w, y - 20, 4, 16, "platform goal")
        self.insert(self.goal)

        # Compress
        self.compress()

    def generate_vertical(self):
        left_bound = -200
        right_bound = 200

        max_height = -300
        min_height = 20

        max_x = 36
        min_x = 10

        max_y_up = 8
        max_y_down = 10
        min_y = 0

        # Starting platform
        self.insert(Prop(((left_bound + right_bound) // 2) - 20, 10, 40, 4, "platform"))

        # Spike floor
        self.insert(Prop(left_bound, min_height, right_bound - left_bound, 4, "platform"))
        self.insert(Prop(left_bound, min_height - 5, right_bound - left_bound, 5, "spike"))

        # Left and right wall
        self.insert(Prop(left_bound, max_height, 4, min_height - max_height + 3, "platform"))
        self.insert(Prop(right_bound - 4, max_height, 4, min_height - max_height + 3, "platform"))

        y = 10
        width = 0
        while y > max_height + 20:
            y -= 20
            x = left_bound
            while x + width < (right_bound):
                delta_x = random.uniform(min_x, max_x)
                delta_y = random.uniform(0, 9) * random.choice([-1, 1])

                width = random.uniform(10, 30)
                x += delta_x + width

                self.insert(Prop(x, y + delta_y, width, 4, "platform"))

            # ensure prop does not extend past wall
            if self.props[-1].x + self.props[-1].width > right_bound:
                self.props.pop()

        # Goal
        self.goal = Prop(left_bound, max_height, right_bound - left_bound, 4, "platform goal")
        self.insert(self.goal)

        # Compress
        self.compress()

    def compress(self):
        self.compressed = json.dumps({"props": [prop.asdict() for prop in self.props]})

    def normalize(self, given, max_, min_):
        return (given - min_)/(max_ - min_)

    def distance(self, x1, y1, x2, y2):
        return sqrt((y2 - y1)**2 + (x2 - x1)**2)

    def insert(self, prop):
        self.props.append(prop)

class Prop(object):
    "Static object on stage"

    def __init__(self, x, y, width, height, proptype):
        self.x = x * Level.GRID
        self.y = y * Level.GRID

        self.width = width * Level.GRID
        self.height = height * Level.GRID

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
            "h": self.height
        }

class Ingredient(object):
    "Collection of props used in level generation"

    def __init__(self, itype, x, y, difficulty):
        self.type = itype
        self.x = x
        self.y = y
        self.x1 = x
        self.y1 = y
        self.x2 = x
        self.y2 = y
        self.props = []

    def add(self, prop):
        self.props.append(prop)

    def place(self, level):
        "Places props in given level"
        level.props.extend(self.props)


# Ingredient subclasses
class IStairs(Ingredient):
    "Series of platforms creating stairs"

    def __init__(self, x, y, difficulty, steps, dx, dy):
        super().__init__("stairs", x, y, difficulty)

        # Generate
        lastspike = False
        for i in range(steps):
            ix = x + dx * i
            iy = y + dy * i
            w = max(dx * .8, 8)
            self.add(Prop(ix, iy, w, 4, "platform"))
            self.x2 = ix + w
            self.y2 = iy
            if not lastspike and random.randint(0, 15) < difficulty and 1 < i < steps - 3:
                self.add(Prop(ix + w // 2 - 2, iy - 5, 5, 5, "spike"))
                lastspike = True
            lastspike = False

class IHorizontal(Ingredient):
    "Single horizontal platform"

    def __init__(self, x, y, difficulty, widthmin, widthmax):
        super().__init__("horizontal", x, y, difficulty)

        # Generate
        w = random.randint(widthmin, widthmax)
        self.add(Prop(x, y, w, 4, "platform"))
        self.x2 = x + w

        if random.randint(0, 12) < difficulty and w > 20:
            self.add(Prop(x + random.randint(10, w - 10), y - 5, random.choice([5, 10, 15, 20]), 5, "spike"))

class IWall(Ingredient):
    "Vertical jumpable wall"

    def __init__(self, x, y, difficulty, maxh):
        super().__init__("wall", x, y, difficulty)

        # Generate
        w = random.randint(16, 64)
        h = round(difficulty * .1 * maxh) - random.randint(0, maxh // 3)
        self.add(
            Prop(x, y, w, 2, "platform"))
        self.add(Prop(x + w // 2, y - 2 - h, 4, h, "platform"))
        self.x2 = x + w

        if difficulty > 2:
            self.add(
                Prop(x + w // 2 - 5,
                    y - random.randint(5, h-5),
                    5, random.randint(1, w // 3) * 5, "spike left"))
