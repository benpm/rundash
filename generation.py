from math import *
import random
import msgpack
import gzip
import json

def build_level(type_, grid = 10):
    return Level(type_, grid)

class Level(object):
    GRID = 10
    def __init__(self, type_, grid = 10):
        self.GRID = grid
        print("Generating Level\nGenerating Level\nGenerating Level")

        self.spawnx = 0
        self.spawny = 7
        
        self.props = []
        

        if type_ is "horizontal":
            self.generate_horizontal()            
        elif type_ is "vertical":
            self.generate_vertical()
        

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
        self.props.append(Prop(x, y, w, h, "platform"))

        # Spike floor
        self.props.append(Prop(-1000, 110, 2000, h, "platform"))
        self.props.append(Prop(-1000, 110 - 5, 2000, 5, "spike"))
        
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

            self.props.append(Prop(x, y, w, h, "platform"))
            
            # Need to base spike probability on normalized values
            if norm_x < 0.9 and plat_vert_sign == 1 and random.random() < .7:
                self.props.append(
                    Prop(x, y - 5, 5, 5, "spike"))
            elif w > 12 and random.random() < 0.6:
                self.props.append(
                    Prop(
                        x + random.randrange(0 if (plat_vert_sign == 1) else 2, round(w / 2), 5) + random.random(),
                        y - 5,
                        5,
                        5,
                        "spike"))
            if w > 25 and random.random() < 0.5:
                self.props.append(
                    Prop(
                        x + random.randrange(round(w / 2) + 2 if plat_vert_sign is 1 else 0 , round(w * .8), 5),
                        y - 5,
                        5,
                        5,
                        "spike"))
                        
        # Goal
        self.goal = Prop(x + 30 + w, y - 20, 4, 16, "platform goal")
        self.props.append(self.goal)

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
        self.props.append(Prop(((left_bound + right_bound) // 2) - 20, 10, 40, 4, "platform"))
        
        # Spike floor
        self.props.append(Prop(left_bound, min_height, right_bound - left_bound, 4, "platform"))
        self.props.append(Prop(left_bound, min_height - 5, right_bound - left_bound, 5, "spike"))

        # Left and right wall
        self.props.append(Prop(left_bound, max_height, 4, min_height - max_height, "platform"))
        self.props.append(Prop(right_bound - 4, max_height, 4, min_height - max_height, "platform"))

        y = 10
        width = 0
        while y > max_height + 20:
            y -= 20
            x = left_bound
            while x + width < (right_bound):
                delta_x = random.uniform(min_x, max_x)
                delta_y = random.uniform(-7, 7)

                width = random.uniform(10, 30)            
                x += delta_x + width

                self.props.append(Prop(x, y + delta_y, width, 4, "platform"))

            # ensure prop does not extend past wall
            if self.props[-1].x + self.props[-1].width > right_bound:
                self.props.pop()

        # Goal
        self.goal = Prop(left_bound, max_height, right_bound - left_bound, 4, "platform goal")
        self.props.append(self.goal)

        # Compress
        self.compress()
        
    def compress(self):
        self.compressed = json.dumps({"props": [prop.asdict() for prop in self.props]})

    def normalize(self, given, max_, min_):
        return (given - min_)/(max_ - min_)

    def distance(self, x1, y1, x2, y2):
        return sqrt((y2 - y1)**2 + (x2 - x1)**2)

class Prop(object):
    "Static object on stage"

    def __init__(self, x, y, w, h, proptype):
        self.x = x * Level.GRID
        self.y = y * Level.GRID
        self.width = w * Level.GRID
        self.height = h * Level.GRID
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