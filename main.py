import pygame
import sys
import random
import asyncio
from pathlib import Path

pygame.init()

WIDTH = 900
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Russian Student Simulator: The Race to the Lecture")
clock = pygame.time.Clock()
IS_WEB = sys.platform == "emscripten"
IS_TOUCH_WEB = False
if IS_WEB:
    import platform

    IS_TOUCH_WEB = int(platform.window.navigator.maxTouchPoints or 0) > 0

font_big = pygame.font.SysFont("arial", 44)
font_medium = pygame.font.SysFont("arial", 28)
font_small = pygame.font.SysFont("arial", 22)
font_label = pygame.font.SysFont("arial", 16)

ASSET_DIR = Path(__file__).parent / "assets"
SUBTITLE_DURATION = 2300
virtual_directions = set()
active_finger_controls = {}
last_finger_event = -1000

mobile_control_rects = {
    "up": pygame.Rect(72, 430, 56, 56),
    "left": pygame.Rect(15, 487, 56, 56),
    "down": pygame.Rect(72, 487, 56, 56),
    "right": pygame.Rect(129, 487, 56, 56),
    "act": pygame.Rect(15, 370, 80, 48),
    "back": pygame.Rect(105, 370, 80, 48),
    "next": pygame.Rect(785, 535, 100, 45),
    "restart": pygame.Rect(365, 535, 170, 45),
}


def load_trimmed_image(filename):
    image = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    bounds = image.get_bounding_rect(min_alpha=8)
    return image.subsurface(bounds).copy() if bounds.width and bounds.height else image


def load_tileset_region(filename, rect):
    sheet = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    image = sheet.subsurface(rect).copy()
    bounds = image.get_bounding_rect(min_alpha=8)
    return image.subsurface(bounds).copy() if bounds.width and bounds.height else image


def load_image_region(filename, rect):
    image = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    return image.subsurface(rect).copy()


def fit_image(image, size):
    width, height = size
    scale = min(width / image.get_width(), height / image.get_height())
    scaled_size = (
        max(1, round(image.get_width() * scale)),
        max(1, round(image.get_height() * scale)),
    )
    return pygame.transform.smoothscale(image, scaled_size)


def cover_image(image, size):
    width, height = size
    scale = max(width / image.get_width(), height / image.get_height())
    scaled = pygame.transform.smoothscale(
        image,
        (
            max(1, round(image.get_width() * scale)),
            max(1, round(image.get_height() * scale)),
        ),
    )
    crop = pygame.Rect(0, 0, width, height)
    crop.center = scaled.get_rect().center
    return scaled.subsurface(crop).copy()


def load_spritesheet(filename, target_height):
    sheet = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    frame_bounds = pygame.mask.from_surface(sheet, 8).get_bounding_rects()
    frames = []

    if len(frame_bounds) == 16:
        frame_bounds.sort(key=lambda rect: rect.centery)
        rows = [
            sorted(frame_bounds[index:index + 4], key=lambda rect: rect.centerx)
            for index in range(0, 16, 4)
        ]
    else:
        rows = []
        for row in range(4):
            row_bounds = []
            top = round(row * sheet.get_height() / 4)
            bottom = round((row + 1) * sheet.get_height() / 4)
            for column in range(4):
                left = round(column * sheet.get_width() / 4)
                right = round((column + 1) * sheet.get_width() / 4)
                row_bounds.append(pygame.Rect(
                    left, top, right - left, bottom - top
                ))
            rows.append(row_bounds)

    for row_bounds in rows:
        row_frames = []
        for bounds in row_bounds:
            frame = sheet.subsurface(bounds).copy()
            target_width = max(
                1, round(frame.get_width() * target_height / frame.get_height())
            )
            row_frames.append(
                pygame.transform.smoothscale(frame, (target_width, target_height))
            )
        frames.append(row_frames)

    return frames


def load_grid_spritesheet(filename, columns, rows, target_height):
    sheet = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    frames = []
    cell_width = sheet.get_width() // columns
    cell_height = sheet.get_height() // rows

    for row in range(rows):
        row_frames = []
        for column in range(columns):
            frame = sheet.subsurface(pygame.Rect(
                column * cell_width,
                row * cell_height,
                cell_width,
                cell_height,
            )).copy()
            bounds = frame.get_bounding_rect(min_alpha=8)
            frame = frame.subsurface(bounds).copy()
            target_width = max(
                1, round(frame.get_width() * target_height / frame.get_height())
            )
            row_frames.append(
                pygame.transform.smoothscale(frame, (target_width, target_height))
            )
        frames.append(row_frames)

    return frames


def load_component_spritesheet(filename, columns, rows, target_height):
    sheet = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    bounds = pygame.mask.from_surface(sheet, 8).get_bounding_rects()
    if len(bounds) != columns * rows:
        raise ValueError(
            f"{filename} contains {len(bounds)} frames, "
            f"expected {columns * rows}"
        )

    bounds.sort(key=lambda rect: rect.centery)
    frames = []
    for row in range(rows):
        row_bounds = sorted(
            bounds[row * columns:(row + 1) * columns],
            key=lambda rect: rect.centerx,
        )
        row_frames = []
        for frame_bounds in row_bounds:
            frame = sheet.subsurface(frame_bounds).copy()
            target_width = max(
                1, round(frame.get_width() * target_height / frame.get_height())
            )
            row_frames.append(
                pygame.transform.smoothscale(frame, (target_width, target_height))
            )
        frames.append(row_frames)

    return frames


floor_image = pygame.image.load(ASSET_DIR / "floor.png").convert()
bathroom_floor_image = pygame.image.load(
    ASSET_DIR / "bathroom_floor.png"
).convert()
hallway_rug_image = load_trimmed_image("hallway_rug.png")

home_asset_sources = {
    "wardrobe": "sliding_wardrobe.png",
    "bed": "bed.png",
    "bedside_table": "bedside_table.png",
    "prayer_corner": "prayer_corner.png",
    "sofa": "sofa.png",
    "coffee_table": "coffee_table.png",
    "floor_lamp": "floor_lamp.png",
    "tv": "TV.png",
    "kitchen_unit": "kitchen_unit.png",
    "fridge": "fridge.png",
    "kitchen_table_set": "kitchen_table_set.png",
    "bath": "bath.png",
    "toilet": "toilet.png",
    "bathroom_sink": "bathroom_sink.png",
    "shoose": "shoose.png",
    "beauty": "beauty.png",
    "clothes": "clothes.png",
}
home_assets = {
    name: load_trimmed_image(filename)
    for name, filename in home_asset_sources.items()
}
home_assets.update({
    "grocery_bag": load_tileset_region(
        "5.png", pygame.Rect(500, 350, 250, 310)
    ),
    "backpack": load_tileset_region(
        "backpack.png", pygame.Rect(35, 220, 275, 410)
    ),
    "student_card": load_trimmed_image("studentid.png"),
    "energy_drink": load_tileset_region(
        "energydrink.png", pygame.Rect(80, 100, 240, 570)
    ),
    "jacket": load_tileset_region(
        "coat.png", pygame.Rect(25, 50, 420, 440)
    ),
})
home_assets["toilet"] = pygame.transform.rotate(home_assets["toilet"], 180)
home_assets["bathroom_sink"] = pygame.transform.rotate(
    home_assets["bathroom_sink"], 180
)
home_assets.update({
    "bathroom_wall": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(45, 40, 349, 140)
    ),
    "bathroom_set_bath": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(918, 39, 363, 231)
    ),
    "bathroom_set_toilet": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(517, 257, 101, 207)
    ),
    "bathroom_set_sink": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(678, 280, 186, 169)
    ),
    "bathroom_washer": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(1339, 67, 129, 222)
    ),
    "bathroom_rug": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(1052, 358, 196, 108)
    ),
    "towel_warmer": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(684, 515, 100, 159)
    ),
    "bathroom_curtain": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(835, 515, 238, 237)
    ),
    "laundry_basket": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(513, 774, 115, 161)
    ),
    "cleaning_shelf": load_tileset_region(
        "bathroom_tileset.png", pygame.Rect(52, 777, 202, 185)
    ),
})
home_assets["bathroom_set_toilet"] = pygame.transform.rotate(
    home_assets["bathroom_set_toilet"], 180
)
home_assets["bathroom_set_sink"] = pygame.transform.rotate(
    home_assets["bathroom_set_sink"], 180
)

player_frames = load_spritesheet("player_spritesheet.png", 52)
mom_frames = load_spritesheet("mom_spritesheet.png", 52)
grandma_frames = load_spritesheet("grandma_spritesheet.png", 51)
sister_frames = load_spritesheet("sister_spritesheet.png", 45)
cat_frames = load_spritesheet("cat_spritesheet.png", 34)
outside_player_frames = load_spritesheet("main-outside.png", 42)
gopnik_frames = load_spritesheet("gopnik_spritesheet.png", 40)
gopnik2_frames = load_spritesheet("gopnik2_.png", 40)
street_granny_frames = load_spritesheet("granny_spritesheet.png", 40)
street_granny2_frames = load_spritesheet("granny2_spritesheet.png", 40)
worker_frames = load_spritesheet("worker_.png", 40)
worker2_frames = load_spritesheet("worker2_.png", 40)
worker3_frames = load_spritesheet("worker3_.png", 40)
student_frames = [
    load_spritesheet(filename, 40)
    for filename in (
        "student.png", "student2.png", "student3.png", "student4.png",
        "student5.png", "student6.png", "student7.png",
    )
]
teacher_frames = [
    load_spritesheet("teacher1.png", 42),
    load_spritesheet("teacher2.png", 42),
]
dekan_frames = load_component_spritesheet("dekan.png", 5, 4, 44)
guard_image = load_tileset_region(
    "guard.png", pygame.Rect(45, 755, 185, 230)
)
full_university_image = pygame.image.load(
    ASSET_DIR / "full_uni.png"
).convert()

outofhome_image = pygame.image.load(
    ASSET_DIR / "scene" / "outofhome.png"
).convert()
bus_wait_image = pygame.image.load(
    ASSET_DIR / "scene" / "bus1.png"
).convert()
bus_broken_image = pygame.image.load(
    ASSET_DIR / "scene" / "bus2.png"
).convert()
before_second_place_image = pygame.image.load(
    ASSET_DIR / "scene" / "beforesecomdplace.png"
).convert()
university_entrance_image = pygame.image.load(
    ASSET_DIR / "scene" / "unientrance.png"
).convert()
university_entrance2_image = pygame.image.load(
    ASSET_DIR / "scene" / "unientrance2.png"
).convert()
dean_scene_image = pygame.image.load(
    ASSET_DIR / "scene" / "dean_scene.png"
).convert()
fail_scene_image = pygame.image.load(
    ASSET_DIR / "scene" / "fail.png"
).convert()
win_scene_image = pygame.image.load(
    ASSET_DIR / "scene" / "win.png"
).convert()
house_image = load_tileset_region(
    "house.png", pygame.Rect(85, 35, 350, 475)
)
tree_image = load_trimmed_image("tree.png")
gopniki_image = load_trimmed_image("gopniki.png")
street_building_images = [
    load_tileset_region("house2.png", rect)
    for rect in (
        pygame.Rect(50, 45, 285, 310),
        pygame.Rect(805, 35, 255, 330),
        pygame.Rect(45, 415, 610, 190),
        pygame.Rect(835, 420, 315, 195),
        pygame.Rect(60, 650, 350, 190),
        pygame.Rect(820, 650, 260, 205),
    )
]
street_roof_images = [
    load_tileset_region("house2.png", rect)
    for rect in (
        pygame.Rect(45, 855, 360, 145),
        pygame.Rect(430, 855, 150, 145),
        pygame.Rect(615, 855, 150, 145),
        pygame.Rect(805, 850, 310, 150),
        pygame.Rect(1140, 855, 165, 145),
        pygame.Rect(1325, 855, 165, 145),
    )
]
snow_image = pygame.image.load(ASSET_DIR / "snow.png").convert()
road_horizontal_image = load_tileset_region(
    "road.png", pygame.Rect(160, 42, 135, 132)
)
road_vertical_image = load_tileset_region(
    "road.png", pygame.Rect(18, 42, 135, 132)
)
road_crossing_image = load_tileset_region(
    "road.png", pygame.Rect(1310, 42, 215, 140)
)
road_lamp_image = load_tileset_region(
    "road.png", pygame.Rect(1000, 745, 58, 165)
)
bus_stop_image = load_tileset_region(
    "busstop.png", pygame.Rect(35, 740, 335, 205)
)
mini_shop_image = load_tileset_region(
    "mni-shop.png", pygame.Rect(45, 590, 320, 250)
)
shop_image = load_tileset_region(
    "shop.png", pygame.Rect(700, 105, 750, 410)
)
university_image = load_tileset_region(
    "uni.png", pygame.Rect(55, 20, 600, 370)
)
park_image = pygame.image.load(ASSET_DIR / "park.png").convert()

# Roof choice and rotation for each city block.
street_building_layout = [
    (0, 0), (1, 0), (3, 0), (4, 90), (0, 0), (2, 0),
    (4, 90), (5, 0), (1, 90), (3, 0), (2, 90), (4, 0), (5, 90),
    (0, 0), (3, 0), (1, 90), (0, 0), (2, 0),
    (4, 90), (5, 0), (0, 0), (1, 90), (3, 0),
]

direction_rows = {"down": 0, "up": 1, "left": 2, "right": 3}
player_direction = "down"
player_moving = False
street_player_direction = "down"
street_player_moving = False
university_player_direction = "down"
university_player_moving = False
scaled_asset_cache = {}
floor_cache = {}

game_state = "intro"
time_left = 30
message = ""
last_hit_time = 0
cutscene_started_at = 0
street_message = ""
street_last_hit_time = 0
bus_used = False
ice_zones_triggered = set()
university_message = ""
university_last_hit_time = 0
university_card_shown = False
jacket_checked = False

player = pygame.Rect(390, 315, 32, 32)
player_speed = 5

student_card = pygame.Rect(295, 285, 34, 24)
backpack = pygame.Rect(600, 338, 32, 42)
jacket = pygame.Rect(785, 475, 42, 44)
energy_drink = pygame.Rect(690, 185, 18, 40)
exit_door = pygame.Rect(598, 535, 34, 25)
has_student_card = False
has_backpack = False
has_jacket = False
has_energy_drink = False

mom = pygame.Rect(475, 455, 32, 32)
grandma = pygame.Rect(755, 455, 32, 32)
cat = pygame.Rect(685, 515, 26, 26)
sister = pygame.Rect(650, 430, 28, 28)

characters = [
    {"rect": mom, "speed": 2, "dx": 2, "dy": 0},
    {"rect": grandma, "speed": 2, "dx": -2, "dy": 0},
    {"rect": cat, "speed": 3, "dx": 3, "dy": 0},
    {"rect": sister, "speed": 2, "dx": 0, "dy": 2},
]

walls = [
    # Outer walls, with the entrance in the bottom wall.
    pygame.Rect(210, 120, 680, 20),
    pygame.Rect(210, 560, 388, 20),
    pygame.Rect(632, 560, 258, 20),
    pygame.Rect(210, 120, 20, 460),
    pygame.Rect(870, 120, 20, 460),

    # Bedroom opens into the living room through the side doorway.
    pygame.Rect(470, 120, 20, 205),
    pygame.Rect(470, 385, 20, 25),

    # The kitchen is wider and has room to walk around the table.
    pygame.Rect(650, 120, 20, 290),

    # Bedroom has no direct doorway into the bathroom or hallway.
    pygame.Rect(210, 390, 280, 20),

    # Living room and kitchen doorways lead into the hallway.
    pygame.Rect(490, 390, 70, 20),
    pygame.Rect(620, 390, 30, 20),
    pygame.Rect(670, 390, 105, 20),
    pygame.Rect(855, 390, 35, 20),

    # Bathroom wall, with a doorway into the hallway.
    pygame.Rect(450, 390, 20, 75),
    pygame.Rect(450, 515, 20, 65),
]

furniture = [
    # Bedroom.
    pygame.Rect(245, 210, 42, 165),   # long sliding wardrobe
    pygame.Rect(325, 140, 105, 145),  # bed against the top wall
    pygame.Rect(438, 175, 28, 45),    # bedside table
    pygame.Rect(232, 142, 48, 46),    # prayer corner tucked into the corner

    # Living room.
    pygame.Rect(505, 142, 120, 45),   # sofa against the back wall
    pygame.Rect(515, 202, 85, 55),    # coffee table closer to the sofa
    pygame.Rect(620, 142, 25, 55),    # floor lamp beside the sofa
    pygame.Rect(625, 230, 25, 105),   # TV

    # Kitchen.
    pygame.Rect(680, 140, 150, 38),   # kitchen counter against the top wall
    pygame.Rect(830, 140, 40, 115),   # refrigerator
    pygame.Rect(745, 205, 105, 125),  # dining table with chairs

    # Bathroom.
    pygame.Rect(240, 420, 125, 52),   # bathtub
    pygame.Rect(245, 500, 36, 50),    # toilet
    pygame.Rect(335, 500, 52, 48),    # sink
    pygame.Rect(395, 418, 45, 58),    # washing machine

    # Hallway.
    pygame.Rect(710, 515, 65, 35),    # clothes stand by the front door
    pygame.Rect(835, 480, 30, 65),    # small hallway wardrobe
    pygame.Rect(680, 415, 75, 25),    # shoe bench by the kitchen entrance

    # Extra room details.
    pygame.Rect(315, 337, 80, 48),    # compact dressing table opposite the bed
    pygame.Rect(682, 342, 26, 31),    # small grocery bag in the kitchen corner
]

furniture_visuals = [
    ("wardrobe", furniture[0]),
    ("bed", furniture[1]),
    ("bedside_table", furniture[2]),
    ("prayer_corner", furniture[3]),
    ("sofa", furniture[4]),
    ("coffee_table", furniture[5]),
    ("floor_lamp", furniture[6]),
    ("tv", furniture[7]),
    ("kitchen_unit", furniture[8]),
    ("fridge", furniture[9]),
    ("kitchen_table_set", furniture[10]),
    ("bathroom_set_bath", furniture[11]),
    ("toilet", furniture[12]),
    ("bathroom_sink", furniture[13]),
    ("bathroom_washer", furniture[14]),
    ("clothes", furniture[15]),
    ("wardrobe", furniture[16]),
    ("shoose", furniture[17]),
    ("beauty", furniture[18]),
    ("grocery_bag", furniture[19]),
]

bathroom_decor_visuals = [
    ("bathroom_rug", pygame.Rect(288, 480, 42, 23)),
]

room_floors = [
    (pygame.Rect(230, 140, 240, 250), (104, 72, 42)),
    (pygame.Rect(490, 140, 160, 250), (104, 72, 42)),
    (pygame.Rect(670, 140, 200, 250), (157, 137, 98)),
    (pygame.Rect(230, 410, 220, 150), (82, 119, 137)),
    (pygame.Rect(470, 410, 400, 150), (104, 72, 42)),
]

# Street level.
street_player = pygame.Rect(35, 185, 20, 20)
street_start = (35, 185)
street_safe_position = street_start
university_entrance = pygame.Rect(775, 480, 35, 18)
bus_stop = pygame.Rect(145, 180, 105, 35)
park_area = pygame.Rect(160, 345, 145, 135)

street_obstacles = [
    pygame.Rect(20, 110, 120, 60),    # home
    pygame.Rect(185, 120, 80, 50),    # bus shelter and kiosk
    pygame.Rect(320, 118, 100, 45),
    pygame.Rect(470, 110, 90, 85),
    pygame.Rect(600, 110, 105, 60),
    pygame.Rect(745, 110, 125, 80),

    pygame.Rect(20, 225, 90, 80),
    pygame.Rect(178, 230, 88, 62),    # shop
    pygame.Rect(300, 220, 65, 75),
    pygame.Rect(420, 235, 100, 55),
    pygame.Rect(605, 220, 90, 80),    # parking
    pygame.Rect(665, 245, 38, 42),    # parking service area
    pygame.Rect(775, 230, 90, 65),    # small residential group

    pygame.Rect(20, 350, 120, 65),
    pygame.Rect(330, 350, 105, 80),
    pygame.Rect(480, 350, 70, 65),    # small residential group
    pygame.Rect(595, 350, 120, 65),
    pygame.Rect(780, 355, 75, 60),    # residential building

    pygame.Rect(20, 465, 110, 75),
    pygame.Rect(320, 480, 95, 55),    # small residential group
    pygame.Rect(455, 475, 110, 65),
    pygame.Rect(600, 460, 95, 80),
    pygame.Rect(760, 498, 110, 62),   # university

    # Trees make the park a small maze instead of a solid wall.
    pygame.Rect(175, 360, 18, 18),
    pygame.Rect(220, 350, 18, 18),
    pygame.Rect(270, 370, 18, 18),
    pygame.Rect(195, 410, 18, 18),
    pygame.Rect(245, 430, 18, 18),
    pygame.Rect(280, 455, 18, 18),
]

ice_zones = [
    pygame.Rect(255, 190, 35, 10),
    pygame.Rect(385, 185, 40, 10),
    pygame.Rect(565, 320, 40, 10),
    pygame.Rect(715, 445, 30, 10),
]

street_people = [
    {
        "rect": pygame.Rect(150, 310, 20, 22),
        "kind": "Grandma",
        "frames": street_granny_frames,
        "color": (185, 120, 235),
        "cost": 3,
        "message": 'Grandma: "Help me with my bags!" -3 min',
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(120, 305, 190, 35),
    },
    {
        "rect": pygame.Rect(445, 310, 22, 22),
        "kind": "Gopnik",
        "frames": gopnik_frames,
        "color": (65, 65, 80),
        "cost": 7,
        "message": 'Gopniks stopped you for a chat. -7 min',
        "dx": 0,
        "dy": 2,
        "bounds": pygame.Rect(440, 305, 35, 165),
    },
    {
        "rect": pygame.Rect(670, 195, 20, 22),
        "kind": "Worker",
        "frames": worker_frames,
        "color": (245, 145, 55),
        "cost": 2,
        "message": 'A worker blocked the pavement. -2 min',
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(565, 190, 300, 30),
    },
    {
        "rect": pygame.Rect(305, 320, 20, 22),
        "kind": "Worker",
        "frames": worker2_frames,
        "color": (245, 145, 55),
        "cost": 2,
        "message": 'A worker asked you to move aside. -2 min',
        "dx": 0,
        "dy": 2,
        "bounds": pygame.Rect(285, 305, 40, 155),
    },
    {
        "rect": pygame.Rect(710, 465, 22, 22),
        "kind": "Gopnik",
        "frames": gopnik2_frames,
        "color": (65, 65, 80),
        "cost": 7,
        "message": 'Gopniks stopped you for a chat. -7 min',
        "dx": 0,
        "dy": -2,
        "bounds": pygame.Rect(700, 420, 35, 140),
    },
    {
        "rect": pygame.Rect(510, 320, 20, 22),
        "kind": "Grandma",
        "frames": street_granny2_frames,
        "color": (175, 115, 220),
        "cost": 3,
        "message": 'Grandma: "Can you show me the way?" -3 min',
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(475, 305, 80, 40),
    },
    {
        "rect": pygame.Rect(370, 445, 20, 22),
        "kind": "Worker",
        "frames": worker3_frames,
        "color": (235, 135, 45),
        "cost": 2,
        "message": 'A worker blocked the pavement. -2 min',
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(315, 430, 115, 40),
    },
]

# University level.
university_player = pygame.Rect(430, 205, 22, 22)
university_start = (430, 205)
university_safe_position = university_start
lecture_entrance = pygame.Rect(530, 455, 205, 110)
guard_zone = pygame.Rect(365, 195, 65, 45)
cloakroom_zone = pygame.Rect(55, 225, 180, 45)

university_obstacles = [
    pygame.Rect(20, 105, 233, 125),   # cloakroom
    pygame.Rect(253, 105, 98, 88),    # notice room
    pygame.Rect(350, 105, 32, 90),    # entrance wall, left side
    pygame.Rect(425, 105, 52, 90),    # entrance wall, right side
    pygame.Rect(477, 105, 73, 96),    # stairs
    pygame.Rect(633, 105, 247, 131),  # cafeteria
    pygame.Rect(20, 232, 196, 115),   # dean's office
    pygame.Rect(20, 352, 196, 181),   # room 101
    pygame.Rect(710, 237, 170, 127),  # room 102
    pygame.Rect(740, 369, 140, 176),  # laboratory
    pygame.Rect(231, 420, 121, 113),  # room 205
    pygame.Rect(359, 394, 184, 139),  # room 206
    pygame.Rect(548, 431, 140, 64),   # lecture hall, upper wall
    pygame.Rect(548, 495, 37, 38),    # lecture hall, left wall
    pygame.Rect(655, 495, 33, 38),    # lecture hall, right wall
    pygame.Rect(340, 285, 48, 28),    # left bench
    pygame.Rect(410, 278, 32, 43),    # vending machine
    pygame.Rect(450, 274, 39, 48),    # central notice board
    pygame.Rect(502, 285, 54, 28),    # right bench
]

university_people = [
    {
        "rect": pygame.Rect(245, 235, 22, 24),
        "kind": "Student",
        "frames": student_frames[0],
        "color": (90, 150, 235),
        "cost": 3,
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(235, 225, 440, 55),
    },
    {
        "rect": pygame.Rect(630, 370, 22, 24),
        "kind": "Student",
        "frames": student_frames[1],
        "color": (110, 185, 225),
        "cost": 3,
        "dx": -2,
        "dy": 0,
        "bounds": pygame.Rect(205, 365, 490, 35),
    },
    {
        "rect": pygame.Rect(570, 300, 22, 24),
        "kind": "Student",
        "frames": student_frames[2],
        "color": (125, 125, 235),
        "cost": 3,
        "dx": 0,
        "dy": 2,
        "bounds": pygame.Rect(565, 230, 45, 175),
    },
    {
        "rect": pygame.Rect(330, 370, 22, 24),
        "kind": "Student",
        "frames": student_frames[3],
        "color": (80, 180, 190),
        "cost": 3,
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(235, 365, 450, 35),
    },
    {
        "rect": pygame.Rect(600, 240, 22, 24),
        "kind": "Student",
        "frames": student_frames[4],
        "color": (170, 125, 225),
        "cost": 3,
        "dx": -2,
        "dy": 0,
        "bounds": pygame.Rect(235, 225, 440, 55),
    },
    {
        "rect": pygame.Rect(400, 340, 22, 24),
        "kind": "Student",
        "frames": student_frames[5],
        "color": (105, 185, 135),
        "cost": 3,
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(305, 335, 290, 35),
    },
    {
        "rect": pygame.Rect(360, 245, 22, 24),
        "kind": "Student",
        "frames": student_frames[6],
        "color": (145, 165, 210),
        "cost": 3,
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(205, 215, 490, 55),
    },
    {
        "rect": pygame.Rect(260, 390, 24, 26),
        "kind": "Teacher",
        "frames": teacher_frames[0],
        "color": (220, 165, 75),
        "cost": 10,
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(205, 385, 490, 35),
    },
    {
        "rect": pygame.Rect(620, 280, 24, 26),
        "kind": "Teacher",
        "frames": teacher_frames[1],
        "color": (220, 165, 75),
        "cost": 10,
        "dx": 0,
        "dy": 2,
        "bounds": pygame.Rect(615, 240, 45, 165),
    },
    {
        "rect": pygame.Rect(250, 240, 26, 28),
        "kind": "Dean",
        "frames": dekan_frames,
        "color": (175, 55, 65),
        "cost": 0,
        "dx": 2,
        "dy": 0,
        "bounds": pygame.Rect(235, 230, 440, 160),
        "route": [(250, 240), (650, 240), (650, 375), (250, 375)],
        "route_index": 1,
        "speed": 2,
    },
]

home_character_initial = [
    (character["rect"].topleft, character["dx"], character["dy"])
    for character in characters
]
street_people_initial = [
    (person["rect"].topleft, person["dx"], person["dy"])
    for person in street_people
]
university_people_initial = [
    (person["rect"].topleft, person["dx"], person["dy"])
    for person in university_people
]


def draw_text(text, x, y, font, color=(255, 255, 255)):
    image = font.render(text, True, color)
    screen.blit(image, (x, y))


def event_matches_key(event, key, characters):
    return event.key == key or event.unicode.lower() in characters


def movement_pressed(keys, key, direction):
    return keys[key] or direction in virtual_directions


def advance_scene():
    global game_state, cutscene_started_at, time_left
    global street_message, street_safe_position

    if game_state == "intro":
        game_state = "home_intro"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "home_intro":
        game_state = "home"
    elif game_state == "home_complete":
        game_state = "exit_cutscene"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "exit_cutscene":
        game_state = "outside_cutscene"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "outside_cutscene":
        game_state = "travel_cutscene"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "travel_cutscene":
        game_state = "street_intro"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "street_intro":
        enter_street()
    elif game_state == "bus_wait":
        time_left -= 4
        street_message = "The bus broke down. You lost 4 min."
        game_state = "bus_broken"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "bus_broken":
        street_safe_position = street_player.topleft
        game_state = "street" if time_left > 0 else "game_over"
    elif game_state == "university_entrance_cutscene":
        game_state = "university_entrance2_cutscene"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "university_entrance2_cutscene":
        game_state = "university_intro"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state == "university_intro":
        enter_university()
    elif game_state == "dean_cutscene":
        game_state = "dean_game_over"


def interact():
    global game_state, cutscene_started_at, message
    global bus_used, university_card_shown
    global jacket_checked, university_message

    if game_state == "home" and player.colliderect(exit_door):
        if has_student_card and has_backpack and has_jacket and has_energy_drink:
            game_state = "exit_cutscene"
            cutscene_started_at = pygame.time.get_ticks()
        else:
            message = "You forgot something!"
    elif game_state == "street" and street_player.colliderect(university_entrance):
        game_state = "university_entrance_cutscene"
        cutscene_started_at = pygame.time.get_ticks()
        university_card_shown = False
        jacket_checked = False
    elif game_state == "street" and street_player.colliderect(bus_stop) and not bus_used:
        bus_used = True
        game_state = "bus_wait"
    elif game_state == "university":
        if university_player.colliderect(guard_zone) and not university_card_shown:
            university_card_shown = True
            university_message = "The guard checked your student card."
        elif university_player.colliderect(cloakroom_zone) and not jacket_checked:
            jacket_checked = True
            university_message = "Your winter jacket is in the cloakroom."
        elif university_player.colliderect(lecture_entrance):
            if university_card_shown and jacket_checked:
                game_state = "victory"
            else:
                university_message = "Complete both entrance tasks first."


def visible_mobile_controls():
    controls = []
    if game_state in ("home", "street", "university"):
        controls.extend(("up", "left", "down", "right", "act"))
    elif game_state in (
        "intro", "home_intro", "home_complete", "exit_cutscene",
        "outside_cutscene", "travel_cutscene", "street_intro",
        "bus_wait", "bus_broken",
        "university_entrance_cutscene", "university_entrance2_cutscene",
        "university_intro", "dean_cutscene",
    ):
        controls.append("next")

    if game_state not in (
        "intro", "game_over", "dean_cutscene", "dean_game_over", "victory"
    ):
        controls.append("back")
    if game_state in ("game_over", "dean_game_over", "victory"):
        controls.append("restart")
    return controls


def mobile_control_at(position):
    for name in visible_mobile_controls():
        if mobile_control_rect(name).collidepoint(position):
            return name
    return None


def mobile_control_rect(name):
    if name == "back" and game_state not in ("home", "street", "university"):
        return pygame.Rect(15, 535, 100, 45)
    return mobile_control_rects[name]


def press_mobile_control(name):
    if name in ("up", "left", "down", "right"):
        virtual_directions.add(name)
    elif name == "act":
        interact()
    elif name == "next":
        advance_scene()
    elif name == "back":
        go_back()
    elif name == "restart":
        reset_game()


def release_mobile_control(name):
    virtual_directions.discard(name)


def draw_mobile_controls():
    if not IS_TOUCH_WEB:
        return

    labels = {
        "act": "ACT",
        "next": "NEXT",
        "back": "BACK",
        "restart": "RESTART",
    }
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for name in visible_mobile_controls():
        rect = mobile_control_rect(name)
        pressed = name in virtual_directions
        pygame.draw.rect(
            overlay, (30, 35, 45, 205 if pressed else 155), rect,
            border_radius=12
        )
        pygame.draw.rect(
            overlay, (255, 235, 150, 210), rect, 2, border_radius=12
        )
        if name in ("up", "left", "down", "right"):
            center_x, center_y = rect.center
            arrow_points = {
                "up": [
                    (center_x, center_y - 13),
                    (center_x - 13, center_y + 10),
                    (center_x + 13, center_y + 10),
                ],
                "left": [
                    (center_x - 13, center_y),
                    (center_x + 10, center_y - 13),
                    (center_x + 10, center_y + 13),
                ],
                "down": [
                    (center_x, center_y + 13),
                    (center_x - 13, center_y - 10),
                    (center_x + 13, center_y - 10),
                ],
                "right": [
                    (center_x + 13, center_y),
                    (center_x - 10, center_y - 13),
                    (center_x - 10, center_y + 13),
                ],
            }
            pygame.draw.polygon(
                overlay, (255, 250, 220), arrow_points[name]
            )
            continue
        label_font = font_small if len(labels[name]) <= 4 else font_label
        label = label_font.render(labels[name], True, (255, 250, 220))
        overlay.blit(label, label.get_rect(center=rect.center))
    screen.blit(overlay, (0, 0))


def draw_centered_text(text, center_y, font, color=(255, 255, 255)):
    image = font.render(text, True, color)
    screen.blit(image, image.get_rect(center=(WIDTH // 2, center_y)))


def draw_info_card(title, lines, footer):
    panel = pygame.Surface((700, 390), pygame.SRCALPHA)
    panel.fill((14, 18, 24, 205))
    pygame.draw.rect(panel, (105, 72, 45, 235), panel.get_rect(), 4)
    screen.blit(panel, panel.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    draw_centered_text(title, 145, font_big, (250, 238, 210))
    line_y = 225
    for line in lines:
        draw_centered_text(line, line_y, font_small, (240, 240, 235))
        line_y += 40
    if IS_TOUCH_WEB:
        footer = (
            "Tap NEXT to start"
            if "start" in footer.lower()
            else "Tap NEXT to continue"
        )
    draw_centered_text(footer, 475, font_medium, (255, 225, 145))


def draw_cutscene_subtitle(text):
    elapsed = pygame.time.get_ticks() - cutscene_started_at
    if elapsed > SUBTITLE_DURATION:
        return

    text_image = font_medium.render(text, True, (255, 255, 255))
    panel_rect = text_image.get_rect()
    panel_rect.width += 50
    panel_rect.height += 24
    bottom_margin = 75 if IS_TOUCH_WEB else 48
    panel_rect.midbottom = (WIDTH // 2, HEIGHT - bottom_margin)
    panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    panel.fill((12, 15, 20, 190))
    screen.blit(panel, panel_rect)
    screen.blit(text_image, text_image.get_rect(center=panel_rect.center))


def enter_street():
    global game_state, street_safe_position, street_message, bus_used
    game_state = "street"
    street_player.topleft = street_start
    street_safe_position = street_start
    street_message = ""
    bus_used = False
    ice_zones_triggered.clear()


def enter_university():
    global game_state, university_safe_position, university_message
    game_state = "university"
    university_player.topleft = university_start
    university_safe_position = university_start
    university_message = ""


def reset_people(people, initial_states):
    for person, (position, dx, dy) in zip(people, initial_states):
        person["rect"].topleft = position
        person["dx"] = dx
        person["dy"] = dy
        if "route" in person:
            person["route_index"] = 1


def reset_game():
    global game_state, time_left, message, last_hit_time
    global cutscene_started_at, street_message, street_last_hit_time
    global bus_used, university_message
    global university_last_hit_time, street_safe_position
    global university_safe_position, has_student_card, has_backpack
    global has_jacket, has_energy_drink, university_card_shown
    global jacket_checked

    game_state = "intro"
    time_left = 30
    message = ""
    last_hit_time = 0
    cutscene_started_at = 0
    street_message = ""
    street_last_hit_time = 0
    bus_used = False
    ice_zones_triggered.clear()
    university_message = ""
    university_last_hit_time = 0
    university_card_shown = False
    jacket_checked = False

    has_student_card = False
    has_backpack = False
    has_jacket = False
    has_energy_drink = False

    player.topleft = (390, 315)
    street_player.topleft = street_start
    street_safe_position = street_start
    university_player.topleft = university_start
    university_safe_position = university_start

    reset_people(characters, home_character_initial)
    reset_people(street_people, street_people_initial)
    reset_people(university_people, university_people_initial)


def go_back():
    global game_state, street_safe_position, university_safe_position
    global street_message, university_message, bus_used, cutscene_started_at

    if game_state == "home_intro":
        game_state = "intro"
    elif game_state == "home":
        game_state = "home_intro"
        cutscene_started_at = pygame.time.get_ticks()
    elif game_state in (
        "home_complete", "exit_cutscene", "outside_cutscene",
        "travel_cutscene", "street_intro"
    ):
        game_state = "home"
        player.topleft = (560, 500)
    elif game_state == "street":
        game_state = "home"
        player.topleft = (560, 500)
    elif game_state == "bus_wait":
        game_state = "street"
        bus_used = False
        street_player.topleft = street_safe_position
    elif game_state == "bus_broken":
        game_state = "street"
        street_safe_position = street_player.topleft
    elif game_state in (
        "university_entrance_cutscene",
        "university_entrance2_cutscene",
        "university_intro",
    ):
        game_state = "street"
        street_player.topleft = street_safe_position
    elif game_state in ("university", "victory"):
        game_state = "street"
        street_player.topleft = street_safe_position
        university_message = ""


def draw_navigation_help():
    if IS_TOUCH_WEB:
        return
    if game_state not in (
        "intro", "game_over", "dean_cutscene", "dean_game_over", "victory"
    ):
        draw_text("B - back", 805, 15, font_small, (225, 225, 210))


def draw_objectives():
    draw_text("Time left: " + str(time_left) + " min", 30, 25, font_small)
    draw_text("Objectives:", 30, 60, font_small)

    draw_text(("✓" if has_student_card else "✗") + " Student card", 30, 95, font_small,
              (120, 255, 120) if has_student_card else (255, 120, 120))
    draw_text(("✓" if has_backpack else "✗") + " Backpack", 30, 125, font_small,
              (120, 255, 120) if has_backpack else (255, 120, 120))
    draw_text(("✓" if has_jacket else "✗") + " Winter jacket", 30, 155, font_small,
              (120, 255, 120) if has_jacket else (255, 120, 120))
    draw_text(("✓" if has_energy_drink else "✗") + " Energy drink", 30, 185, font_small,
              (120, 255, 120) if has_energy_drink else (255, 120, 120))


def draw_asset(name, rect):
    cache_key = (name, rect.size)
    if cache_key not in scaled_asset_cache:
        scaled_asset_cache[cache_key] = pygame.transform.smoothscale(
            home_assets[name], rect.size
        )
    image = scaled_asset_cache[cache_key]
    screen.blit(image, rect)


def draw_floor(texture, rect, texture_name):
    cache_key = (texture_name, rect.size)
    if cache_key not in floor_cache:
        floor_cache[cache_key] = cover_image(texture, rect.size)
    screen.blit(floor_cache[cache_key], rect)


def draw_character(frames, rect, direction, moving=True, feet_offset=3):
    row = direction_rows[direction]
    frame_count = len(frames[row])
    frame_index = (
        (pygame.time.get_ticks() // 140) % frame_count if moving else 0
    )
    image = frames[row][frame_index]
    image_rect = image.get_rect()
    image_rect.midbottom = (rect.centerx, rect.bottom + feet_offset)
    screen.blit(image, image_rect)


def character_direction(character):
    if character["dx"] < 0:
        return "left"
    if character["dx"] > 0:
        return "right"
    if character["dy"] < 0:
        return "up"
    return "down"


def draw_home():
    pygame.draw.rect(screen, (64, 43, 28), (210, 120, 680, 460))

    for index, (floor, color) in enumerate(room_floors):
        if index == 3:
            texture = bathroom_floor_image
            texture_name = "bathroom"
        else:
            texture = floor_image
            texture_name = "wood"
        draw_floor(texture, floor, texture_name)

    rug_rect = pygame.Rect(555, 435, 180, 105)
    rug_key = ("hallway_rug", rug_rect.size)
    if rug_key not in scaled_asset_cache:
        scaled_asset_cache[rug_key] = fit_image(hallway_rug_image, rug_rect.size)
    rug = scaled_asset_cache[rug_key]
    rug_position = rug.get_rect(center=rug_rect.center)
    screen.blit(rug, rug_position)

    for wall in walls:
        pygame.draw.rect(screen, (155, 120, 85), wall)

    for name, rect in furniture_visuals:
        draw_asset(name, rect)

    # Small bathroom details do not affect movement or collision.
    for name, rect in bathroom_decor_visuals:
        draw_asset(name, rect)
    draw_asset("bathroom_curtain", pygame.Rect(240, 416, 125, 55))

def hits_obstacle(rect):
    for wall in walls:
        if rect.colliderect(wall):
            return True
    for item in furniture:
        if rect.colliderect(item):
            return True
    return False


def keep_inside_apartment(rect):
    if rect.left < 230:
        rect.left = 230
    if rect.right > 870:
        rect.right = 870
    if rect.top < 140:
        rect.top = 140
    if rect.bottom > 560:
        rect.bottom = 560


def move_player():
    global player_direction, player_moving

    old_x = player.x
    old_y = player.y

    keys = pygame.key.get_pressed()
    player_moving = False

    if movement_pressed(keys, pygame.K_LEFT, "left"):
        player.x -= player_speed
        player_direction = "left"
        player_moving = True
    if movement_pressed(keys, pygame.K_RIGHT, "right"):
        player.x += player_speed
        player_direction = "right"
        player_moving = True
    if movement_pressed(keys, pygame.K_UP, "up"):
        player.y -= player_speed
        player_direction = "up"
        player_moving = True
    if movement_pressed(keys, pygame.K_DOWN, "down"):
        player.y += player_speed
        player_direction = "down"
        player_moving = True

    keep_inside_apartment(player)

    if hits_obstacle(player):
        player.x = old_x
        player.y = old_y
        player_moving = False


def choose_new_direction(character):
    speed = character["speed"]
    direction = random.choice(["left", "right", "up", "down"])

    if direction == "left":
        character["dx"] = -speed
        character["dy"] = 0
    elif direction == "right":
        character["dx"] = speed
        character["dy"] = 0
    elif direction == "up":
        character["dx"] = 0
        character["dy"] = -speed
    elif direction == "down":
        character["dx"] = 0
        character["dy"] = speed


def move_characters():
    for character in characters:
        rect = character["rect"]

        if random.randint(1, 20) == 1:
            choose_new_direction(character)

        old_x = rect.x
        old_y = rect.y

        rect.x += character["dx"]
        keep_inside_apartment(rect)

        if hits_obstacle(rect):
            rect.x = old_x
            choose_new_direction(character)

        rect.y += character["dy"]
        keep_inside_apartment(rect)

        if hits_obstacle(rect):
            rect.y = old_y
            choose_new_direction(character)


def street_hits_obstacle(rect):
    return any(rect.colliderect(obstacle) for obstacle in street_obstacles)


def move_street_player():
    global street_player_direction, street_player_moving

    old_position = street_player.topleft
    keys = pygame.key.get_pressed()

    dx = 0
    dy = 0
    street_player_moving = False
    if movement_pressed(keys, pygame.K_LEFT, "left"):
        dx -= player_speed
        street_player_direction = "left"
        street_player_moving = True
    if movement_pressed(keys, pygame.K_RIGHT, "right"):
        dx += player_speed
        street_player_direction = "right"
        street_player_moving = True
    if movement_pressed(keys, pygame.K_UP, "up"):
        dy -= player_speed
        street_player_direction = "up"
        street_player_moving = True
    if movement_pressed(keys, pygame.K_DOWN, "down"):
        dy += player_speed
        street_player_direction = "down"
        street_player_moving = True

    street_player.x += dx
    street_player.left = max(20, street_player.left)
    street_player.right = min(WIDTH - 20, street_player.right)
    if street_hits_obstacle(street_player):
        street_player.x = old_position[0]

    street_player.y += dy
    street_player.top = max(110, street_player.top)
    street_player.bottom = min(570, street_player.bottom)
    if street_hits_obstacle(street_player):
        street_player.y = old_position[1]

    return old_position


def move_street_people():
    for person in street_people:
        rect = person["rect"]
        old_position = rect.topleft
        rect.x += person["dx"]
        rect.y += person["dy"]

        if not person["bounds"].contains(rect) or street_hits_obstacle(rect):
            rect.topleft = old_position
            person["dx"] *= -1
            person["dy"] *= -1


def draw_exit_cutscene():
    image = cover_image(outofhome_image, (WIDTH, HEIGHT))
    screen.blit(image, (0, 0))
    draw_cutscene_subtitle("You finally escaped the apartment.")
    if not IS_TOUCH_WEB:
        draw_text("SPACE - skip", 745, 565, font_small, (190, 205, 220))


def draw_outside_cutscene():
    elapsed = pygame.time.get_ticks() - cutscene_started_at
    screen.fill((178, 190, 202))
    pygame.draw.rect(screen, (222, 225, 226), (0, 420, WIDTH, 180))
    pygame.draw.rect(screen, (165, 174, 181), (0, 485, WIDTH, 80))

    background_houses = [
        (street_building_images[0], (285, 355), (135, 485)),
        (street_building_images[0], (285, 355), (765, 485)),
    ]
    for building_image, size, position in background_houses:
        building = fit_image(building_image, size)
        screen.blit(building, building.get_rect(midbottom=position))

    house = fit_image(house_image, (430, 440))
    screen.blit(house, house.get_rect(midbottom=(450, 485)))

    tree_sizes_and_positions = [
        ((72, 215), (95, 500)),
        ((88, 255), (185, 500)),
        ((62, 185), (275, 495)),
        ((62, 185), (625, 495)),
        ((88, 255), (715, 500)),
        ((72, 215), (805, 500)),
    ]
    for size, position in tree_sizes_and_positions:
        tree = fit_image(tree_image, size)
        screen.blit(tree, tree.get_rect(midbottom=position))

    gopniki = fit_image(gopniki_image, (105, 64))
    screen.blit(gopniki, gopniki.get_rect(midbottom=(565, 498)))

    progress = min(1.0, elapsed / 2600)
    cutscene_player = pygame.Rect(
        round(430 - 95 * progress), round(420 + 60 * progress), 50, 70
    )
    frame_index = (pygame.time.get_ticks() // 140) % 4
    player_image = outside_player_frames[direction_rows["left"]][frame_index]
    player_image = pygame.transform.smoothscale(
        player_image,
        (
            round(player_image.get_width() * 70 / player_image.get_height()),
            70,
        ),
    )
    screen.blit(
        player_image,
        player_image.get_rect(midbottom=cutscene_player.midbottom),
    )

    draw_cutscene_subtitle("The cold hits immediately.")
    if not IS_TOUCH_WEB:
        draw_text("SPACE - skip", 745, 565, font_small, (70, 75, 85))


def draw_travel_cutscene():
    elapsed = pygame.time.get_ticks() - cutscene_started_at
    screen.fill((14, 17, 22))
    image = fit_image(before_second_place_image, (WIDTH - 50, HEIGHT - 20))
    screen.blit(image, image.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    progress = min(1.0, elapsed / 3000)
    player_rect = pygame.Rect(round(110 + 650 * progress), 490, 34, 45)
    frame_index = (pygame.time.get_ticks() // 140) % 4
    player_image = outside_player_frames[direction_rows["right"]][frame_index]
    screen.blit(
        player_image,
        player_image.get_rect(midbottom=player_rect.midbottom),
    )

    draw_cutscene_subtitle("The city is already moving.")
    if not IS_TOUCH_WEB:
        draw_text("SPACE - skip", 745, 565, font_small, (210, 220, 230))


def draw_street():
    screen.fill((145, 180, 205))
    city_bounds = pygame.Rect(20, 105, 860, 465)
    draw_floor(snow_image, city_bounds, "street_snow")

    horizontal_roads = [
        pygame.Rect(20, 175, 850, 45),
        pygame.Rect(20, 305, 850, 40),
        pygame.Rect(20, 430, 850, 35),
    ]
    vertical_roads = [
        pygame.Rect(140, 105, 35, 455),
        pygame.Rect(275, 105, 35, 455),
        pygame.Rect(435, 105, 35, 455),
        pygame.Rect(560, 105, 35, 455),
        pygame.Rect(715, 105, 40, 455),
    ]
    for index, road in enumerate(horizontal_roads):
        draw_floor(road_horizontal_image, road, f"road_horizontal_{index}")
    for index, road in enumerate(vertical_roads):
        draw_floor(road_vertical_image, road, f"road_vertical_{index}")

    for x in (140, 275, 435, 560, 715):
        crossing = pygame.Rect(x - 4, 300, 44, 48)
        draw_floor(road_crossing_image, crossing, f"road_crossing_{x}")

    draw_floor(park_image, park_area, "street_park")

    for index, obstacle in enumerate(street_obstacles):
        if index >= 23:
            continue

        if index == 1:
            kiosk_bounds = pygame.Rect(188, 132, 31, 32)
            kiosk = fit_image(mini_shop_image, kiosk_bounds.size)
            screen.blit(kiosk, kiosk.get_rect(center=kiosk_bounds.center))
            continue
        if index == 7:
            shop_bounds = pygame.Rect(178, 230, 88, 62)
            building = fit_image(shop_image, shop_bounds.size)
            screen.blit(building, building.get_rect(center=shop_bounds.center))
            continue
        if index == 11:
            continue
        if index == 22:
            building = fit_image(university_image, obstacle.size)
            screen.blit(building, building.get_rect(center=obstacle.center))
            continue
        if index in (12, 15, 19):
            cluster_roofs = (
                street_roof_images[1],
                street_roof_images[2],
            )
            left_lot = pygame.Rect(0, 0, obstacle.width // 2 - 5, obstacle.height - 14)
            right_lot = left_lot.copy()
            left_lot.midleft = (obstacle.left + 4, obstacle.centery)
            right_lot.midright = (obstacle.right - 4, obstacle.centery)

            for roof, lot in zip(cluster_roofs, (left_lot, right_lot)):
                building = fit_image(roof, lot.size)
                screen.blit(building, building.get_rect(center=lot.center))
            continue

        roof_index, rotation = street_building_layout[index]
        building = street_roof_images[roof_index]
        if rotation:
            building = pygame.transform.rotate(building, rotation)

        visual_bounds = obstacle.inflate(-24, -14)
        if index == 2:
            visual_bounds = pygame.Rect(330, 125, 80, 32)
        elif index == 8:
            visual_bounds = pygame.Rect(310, 228, 45, 58)
        elif index == 9:
            visual_bounds = pygame.Rect(432, 243, 76, 36)

        building = fit_image(building, visual_bounds.size)
        screen.blit(
            building,
            building.get_rect(center=visual_bounds.center),
        )

    lamp = fit_image(road_lamp_image, (14, 42))
    for position in (
        (185, 225), (255, 295), (325, 285), (395, 415),
        (530, 235), (610, 335), (685, 410), (770, 335),
        (840, 465),
    ):
        screen.blit(lamp, lamp.get_rect(midbottom=position))

    for index, ice in enumerate(ice_zones):
        color = (130, 205, 235) if index not in ice_zones_triggered else (155, 190, 210)
        pygame.draw.rect(screen, color, ice)
        pygame.draw.rect(screen, (225, 250, 255), ice, 2)

    # The shelter is decorative; the original rectangle remains interactive.
    shelter = fit_image(bus_stop_image, (38, 24))
    screen.blit(shelter, shelter.get_rect(midbottom=(245, 164)))
    bus_label = font_label.render(
        "BUS STOP - press E", True, (255, 245, 175)
    )
    bus_label_panel = pygame.Surface(
        (bus_label.get_width() + 16, bus_label.get_height() + 8),
        pygame.SRCALPHA,
    )
    bus_label_panel.fill((25, 45, 65, 220))
    bus_label_rect = bus_label_panel.get_rect(midbottom=(230, 130))
    screen.blit(bus_label_panel, bus_label_rect)
    screen.blit(bus_label, bus_label.get_rect(center=bus_label_rect.center))

    for person in street_people:
        draw_character(
            person["frames"],
            person["rect"],
            character_direction(person),
            moving=True,
            feet_offset=1,
        )

    draw_character(
        outside_player_frames, street_player, street_player_direction,
        moving=street_player_moving, feet_offset=1
    )

    draw_text("CITY", 415, 15, font_medium)
    draw_text("Time left: " + str(time_left) + " min", 25, 20, font_small)
    draw_text("Reach the university", 25, 55, font_small)
    if street_message:
        draw_text(street_message, 245, 70, font_small, (170, 40, 40))

    if street_player.colliderect(university_entrance):
        draw_text("Press E to enter the university", 585, 455, font_small,
                  (255, 245, 120))
    elif street_player.colliderect(bus_stop) and not bus_used:
        draw_text("Press E to wait for the bus", 120, 220, font_small,
                  (255, 245, 120))


def draw_bus_cutscene(image, subtitle):
    screen.blit(cover_image(image, (WIDTH, HEIGHT)), (0, 0))
    draw_cutscene_subtitle(subtitle)
    if not IS_TOUCH_WEB:
        draw_text("SPACE - continue", 700, 565, font_small, (220, 225, 235))


def university_hits_obstacle(rect):
    return any(rect.colliderect(obstacle) for obstacle in university_obstacles)


def move_university_player():
    global university_player_direction, university_player_moving

    old_position = university_player.topleft
    keys = pygame.key.get_pressed()

    dx = 0
    dy = 0
    university_player_moving = False
    if movement_pressed(keys, pygame.K_LEFT, "left"):
        dx -= player_speed
        university_player_direction = "left"
        university_player_moving = True
    if movement_pressed(keys, pygame.K_RIGHT, "right"):
        dx += player_speed
        university_player_direction = "right"
        university_player_moving = True
    if movement_pressed(keys, pygame.K_UP, "up"):
        dy -= player_speed
        university_player_direction = "up"
        university_player_moving = True
    if movement_pressed(keys, pygame.K_DOWN, "down"):
        dy += player_speed
        university_player_direction = "down"
        university_player_moving = True

    university_player.x += dx
    university_player.left = max(20, university_player.left)
    university_player.right = min(WIDTH - 20, university_player.right)
    if university_hits_obstacle(university_player):
        university_player.x = old_position[0]

    university_player.y += dy
    university_player.top = max(110, university_player.top)
    university_player.bottom = min(570, university_player.bottom)
    if university_hits_obstacle(university_player):
        university_player.y = old_position[1]


def move_university_people():
    for person in university_people:
        rect = person["rect"]

        if "route" in person:
            target_x, target_y = person["route"][person["route_index"]]
            delta_x = target_x - rect.x
            delta_y = target_y - rect.y
            speed = person["speed"]

            if abs(delta_x) <= speed and abs(delta_y) <= speed:
                rect.topleft = (target_x, target_y)
                person["route_index"] = (
                    person["route_index"] + 1
                ) % len(person["route"])
                continue

            person["dx"] = (
                min(speed, delta_x) if delta_x > 0
                else max(-speed, delta_x) if delta_x < 0
                else 0
            )
            person["dy"] = (
                min(speed, delta_y) if delta_y > 0
                else max(-speed, delta_y) if delta_y < 0
                else 0
            )
            old_position = rect.topleft
            rect.x += person["dx"]
            rect.y += person["dy"]
            if university_hits_obstacle(rect):
                rect.topleft = old_position
                person["route_index"] = (
                    person["route_index"] + 1
                ) % len(person["route"])
            continue

        old_position = rect.topleft
        rect.x += person["dx"]
        rect.y += person["dy"]

        if not person["bounds"].contains(rect) or university_hits_obstacle(rect):
            rect.topleft = old_position
            person["dx"] *= -1
            person["dy"] *= -1


def draw_university_entrance_cutscene(image, caption):
    scene = cover_image(image, (WIDTH, HEIGHT))
    screen.blit(scene, (0, 0))
    draw_cutscene_subtitle(caption)
    if not IS_TOUCH_WEB:
        draw_text("SPACE - skip", 745, 565, font_small, (220, 225, 230))


def draw_dean_cutscene():
    scene = cover_image(dean_scene_image, (WIDTH, HEIGHT))
    screen.blit(scene, (0, 0))
    draw_text("SPACE - continue", 700, 565, font_small, (235, 220, 185))


def draw_result_scene(image, title, subtitle):
    scene = cover_image(image, (WIDTH, HEIGHT))
    screen.blit(scene, (0, 0))

    panel = pygame.Surface((620, 110), pygame.SRCALPHA)
    panel.fill((10, 12, 15, 205))
    panel_rect = panel.get_rect(midtop=(WIDTH // 2, 25))
    screen.blit(panel, panel_rect)
    draw_centered_text(title, 55, font_big, (255, 235, 190))
    draw_centered_text(subtitle, 98, font_small, (245, 245, 240))
    draw_text("R / К - restart", 720, 565, font_label, (255, 235, 190))


def draw_lecture_finish_marker():
    label = font_small.render("FINISH", True, (255, 220, 70))
    screen.blit(label, label.get_rect(center=(620, 520)))


def draw_university():
    screen.fill((35, 39, 43))
    university_bounds = pygame.Rect(20, 105, 860, 465)
    cache_key = ("full_university", university_bounds.size)
    if cache_key not in scaled_asset_cache:
        scaled_asset_cache[cache_key] = pygame.transform.smoothscale(
            full_university_image, university_bounds.size
        )
    screen.blit(scaled_asset_cache[cache_key], university_bounds)
    draw_lecture_finish_marker()

    # Static guard for the entrance objective.
    guard = fit_image(guard_image, (34, 44))
    screen.blit(guard, guard.get_rect(midbottom=(390, 235)))

    for person in university_people:
        draw_character(
            person["frames"],
            person["rect"],
            character_direction(person),
            moving=True,
            feet_offset=1,
        )
        if person["kind"] in ("Teacher", "Dean"):
            label = font_label.render(
                person["kind"], True, (245, 230, 175)
            )
            label_rect = label.get_rect(
                midbottom=(person["rect"].centerx, person["rect"].top - 3)
            )
            screen.blit(label, label_rect)

    university_frames = (
        player_frames if jacket_checked else outside_player_frames
    )
    draw_character(
        university_frames,
        university_player,
        university_player_direction,
        moving=university_player_moving,
        feet_offset=1,
    )

    draw_text("UNIVERSITY", 365, 15, font_medium)
    draw_text("Time left: " + str(time_left) + " min", 25, 20, font_small)
    draw_text(("✓" if university_card_shown else "✗") + " Show student card",
              25, 50, font_small,
              (120, 255, 120) if university_card_shown else (255, 150, 130))
    draw_text(("✓" if jacket_checked else "✗") + " Leave winter jacket",
              25, 75, font_small,
              (120, 255, 120) if jacket_checked else (255, 150, 130))
    if university_message:
        draw_text(university_message, 315, 75, font_small, (255, 205, 105))

    if university_player.colliderect(guard_zone) and not university_card_shown:
        draw_text("Press E to show your student card", 325, 200, font_small,
                  (255, 245, 120))
    elif university_player.colliderect(cloakroom_zone) and not jacket_checked:
        draw_text("Press E to leave your jacket", 215, 220, font_small,
                  (255, 245, 120))
    elif university_player.colliderect(lecture_entrance):
        if university_card_shown and jacket_checked:
            prompt = "Entering the lecture hall..."
        else:
            prompt = "Complete both entrance tasks first"
        draw_text(prompt, 315, 515, font_small,
                  (255, 245, 120))


async def main():
    global game_state, cutscene_started_at, message
    global bus_used, university_card_shown
    global jacket_checked, has_student_card, has_backpack
    global has_jacket, has_energy_drink, time_left, last_hit_time
    global street_last_hit_time, street_message, street_safe_position
    global university_last_hit_time, university_message
    global university_safe_position
    global last_finger_event

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if IS_TOUCH_WEB and event.type == pygame.FINGERDOWN:
                last_finger_event = pygame.time.get_ticks()
                position = (round(event.x * WIDTH), round(event.y * HEIGHT))
                control = mobile_control_at(position)
                if control:
                    active_finger_controls[event.finger_id] = control
                    press_mobile_control(control)

            if IS_TOUCH_WEB and event.type == pygame.FINGERMOTION:
                last_finger_event = pygame.time.get_ticks()
                position = (round(event.x * WIDTH), round(event.y * HEIGHT))
                old_control = active_finger_controls.get(event.finger_id)
                new_control = mobile_control_at(position)
                if old_control != new_control:
                    if old_control:
                        release_mobile_control(old_control)
                    if new_control:
                        active_finger_controls[event.finger_id] = new_control
                        press_mobile_control(new_control)
                    else:
                        active_finger_controls.pop(event.finger_id, None)

            if IS_TOUCH_WEB and event.type == pygame.FINGERUP:
                last_finger_event = pygame.time.get_ticks()
                control = active_finger_controls.pop(event.finger_id, None)
                if control:
                    release_mobile_control(control)

            if (
                IS_TOUCH_WEB
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and pygame.time.get_ticks() - last_finger_event > 500
            ):
                control = mobile_control_at(event.pos)
                if control:
                    active_finger_controls["mouse"] = control
                    press_mobile_control(control)

            if (
                IS_TOUCH_WEB
                and event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
            ):
                control = active_finger_controls.pop("mouse", None)
                if control:
                    release_mobile_control(control)

            if event.type == pygame.KEYDOWN:
                if event_matches_key(event, pygame.K_b, ("b", "и")):
                    go_back()
    
                if event_matches_key(event, pygame.K_r, ("r", "к")) and game_state in (
                    "game_over", "dean_game_over", "victory"
                ):
                    reset_game()

                if event.key == pygame.K_SPACE:
                    advance_scene()

                if event.key in (pygame.K_e, pygame.K_RETURN):
                    interact()
    
        if game_state == "home":
            move_player()
            move_characters()
    
            if player.colliderect(student_card):
                has_student_card = True
            if player.colliderect(backpack):
                has_backpack = True
            if player.colliderect(jacket):
                has_jacket = True
            if player.colliderect(energy_drink):
                has_energy_drink = True
    
            current_time = pygame.time.get_ticks()
    
            if player.colliderect(mom) and current_time - last_hit_time > 1000:
                time_left -= 5
                last_hit_time = current_time
                message = 'Mom: "Why are you still not at university?" -5 min'
    
            if player.colliderect(grandma) and current_time - last_hit_time > 1000:
                time_left -= 10
                last_hit_time = current_time
                message = 'Grandma: "Do you want to eat something?" -10 min'
    
            if player.colliderect(cat) and current_time - last_hit_time > 1000:
                time_left -= 1
                last_hit_time = current_time
                message = "The cat blocked your way. -1 min"
    
            if player.colliderect(sister) and current_time - last_hit_time > 1000:
                time_left -= 5
                last_hit_time = current_time
                questions = [
                    'Sister: "Where are you going?" -5 min',
                    'Sister: "When will you come back?" -5 min',
                    'Sister: "Will we play later?" -5 min',
                    'Sister: "Can I take your stuff?" -5 min'
                ]
                message = random.choice(questions)
    
            if time_left <= 0:
                game_state = "game_over"
    
        elif game_state == "street":
            move_street_player()
            move_street_people()
            current_time = pygame.time.get_ticks()
            hit_person = False
    
            for person in street_people:
                if street_player.colliderect(person["rect"]):
                    hit_person = True
                    street_player.topleft = street_safe_position
                    if current_time - street_last_hit_time > 1200:
                        time_left -= person["cost"]
                        street_last_hit_time = current_time
                        street_message = person["message"]
                    break
    
            if not hit_person:
                street_safe_position = street_player.topleft
    
            for index, ice in enumerate(ice_zones):
                if street_player.colliderect(ice) and index not in ice_zones_triggered:
                    ice_zones_triggered.add(index)
                    time_left -= 2
                    street_message = "You slipped on the ice. -2 min"
    
            if time_left <= 0:
                game_state = "game_over"
    
        elif game_state == "university":
            move_university_player()
            move_university_people()
            current_time = pygame.time.get_ticks()
            hit_person = False
    
            for person in university_people:
                if university_player.colliderect(person["rect"]):
                    hit_person = True
                    university_player.topleft = university_safe_position
    
                    if person["kind"] == "Dean":
                        game_state = "dean_cutscene"
                        break
    
                    if current_time - university_last_hit_time > 1200:
                        university_last_hit_time = current_time
                        time_left -= person["cost"]
                        if person["kind"] == "Teacher":
                            university_message = (
                                'Teacher: "Why are you not in class yet?" -10 min'
                            )
                        else:
                            university_message = random.choice([
                                'Student: "Watch where you are going!" -3 min',
                                'Student: "Do you know where room 211 is?" -3 min',
                                'Student: "Coffee after class?" -3 min',
                            ])
                    break
    
            if not hit_person:
                university_safe_position = university_player.topleft
    
            if (
                university_player.colliderect(lecture_entrance)
                and university_card_shown
                and jacket_checked
            ):
                game_state = "victory"
    
            if time_left <= 0:
                game_state = "game_over"
    
        if game_state == "intro":
            screen.fill((20, 25, 50))
            draw_info_card(
                "Russian Student Simulator",
                [
                    "The Race to the Lecture",
                    "You overslept.",
                    "Outside: -27°C",
                    "The lecture starts in 30 minutes.",
                ],
                "Press SPACE to start",
            )
    
        elif game_state == "home_intro":
            screen.fill((80, 55, 35))
            draw_info_card(
                "HOME",
                [
                    "Collect your student card, backpack, jacket and energy drink.",
                    "Mom's questions take 5 minutes.",
                    "Grandma's invitation takes 10 minutes - she is hard to refuse.",
                    "Your sister takes 5 minutes, and the cat takes 1 minute.",
                    "Reach the front door when you are ready.",
                ],
                "SPACE - continue",
            )
    
        elif game_state == "home":
            screen.fill((100, 75, 50))
    
            draw_home()
            draw_text("Home level", 370, 35, font_medium)
            draw_text("Use arrow keys to move", 320, 75, font_small)
            draw_objectives()
    
            if not has_student_card:
                draw_asset("student_card", student_card)
            if not has_backpack:
                draw_asset("backpack", backpack)
            if not has_jacket:
                draw_asset("jacket", jacket)
            if not has_energy_drink:
                draw_asset("energy_drink", energy_drink)
    
            pygame.draw.rect(screen, (90, 45, 20), exit_door)
            draw_text("Door", 592, 510, font_small)
    
            draw_character(
                mom_frames, mom, character_direction(characters[0]), moving=True
            )
            draw_character(
                grandma_frames, grandma, character_direction(characters[1]), moving=True
            )
            draw_character(
                cat_frames, cat, character_direction(characters[2]), moving=True,
                feet_offset=1
            )
            draw_character(
                sister_frames, sister, character_direction(characters[3]), moving=True
            )
            draw_character(
                player_frames, player, player_direction, moving=player_moving
            )
    
            draw_text("Mom", mom.x - 5, mom.y - 25, font_small)
            draw_text("Grandma", grandma.x - 25, grandma.y - 25, font_small)
            draw_text("Cat", cat.x - 2, cat.y - 25, font_small)
            draw_text("Sister", sister.x - 15, sister.y - 25, font_small)
    
            if message != "":
                draw_text(message, 230, 485, font_small, (255, 255, 120))
    
            if player.colliderect(exit_door):
                if has_student_card and has_backpack and has_jacket and has_energy_drink:
                    draw_text("Press E or ENTER to leave", 275, 530, font_medium)
                else:
                    draw_text("You still need all required items", 220, 530, font_medium)
    
        elif game_state == "home_complete":
            screen.fill((35, 45, 70))
            draw_info_card(
                "First stage complete!",
                [
                    "Student card, backpack, jacket and energy drink collected.",
                    "Time left: " + str(time_left) + " minutes.",
                    "You escaped the apartment.",
                ],
                "SPACE - continue",
            )
    
        elif game_state == "exit_cutscene":
            draw_exit_cutscene()
    
        elif game_state == "outside_cutscene":
            draw_outside_cutscene()
    
        elif game_state == "travel_cutscene":
            draw_travel_cutscene()
    
        elif game_state == "street_intro":
            screen.fill((40, 70, 100))
            draw_info_card(
                "STREET",
                [
                    "Reach the university before the lecture starts.",
                    "Helping a grandma takes 3 minutes.",
                    "Gopniks delay you by 7 minutes; workers take 2 minutes.",
                    "Slipping on ice takes 2 minutes. The bus may save time.",
                    "Time left: " + str(time_left) + " minutes.",
                ],
                "SPACE - continue",
            )
    
        elif game_state == "street":
            draw_street()
    
        elif game_state == "bus_wait":
            draw_bus_cutscene(
                bus_wait_image,
                "You wait at the bus stop, hoping to save time.",
            )

        elif game_state == "bus_broken":
            draw_bus_cutscene(
                bus_broken_image,
                "Time passes... but the bus breaks down. You lose 4 minutes.",
            )
    
        elif game_state == "university_entrance_cutscene":
            draw_university_entrance_cutscene(
                university_entrance_image,
                "You finally reached the university.",
            )
    
        elif game_state == "university_entrance2_cutscene":
            draw_university_entrance_cutscene(
                university_entrance2_image,
                "Just two entrance checks left.",
            )
    
        elif game_state == "university_intro":
            screen.fill((45, 55, 80))
            draw_info_card(
                "UNIVERSITY",
                [
                    "Show your student card and leave your jacket.",
                    "A teacher's questions take 10 minutes.",
                    "A conversation with a student takes 3 minutes.",
                    "The dean sends late students to write an explanatory note.",
                    "Time left: " + str(time_left) + " minutes.",
                ],
                "SPACE - continue",
            )
    
        elif game_state == "university":
            draw_university()
    
        elif game_state == "dean_cutscene":
            draw_dean_cutscene()
    
        elif game_state == "victory":
            draw_result_scene(
                win_scene_image,
                "YOU MADE IT!",
                "The lecture started with " + str(time_left) + " minutes left.",
            )
    
        elif game_state == "dean_game_over":
            draw_result_scene(
                fail_scene_image,
                "YOU LOST",
                "The dean sent you to write an explanatory note.",
            )
    
        elif game_state == "game_over":
            draw_result_scene(
                fail_scene_image,
                "YOU ARE LATE",
                "The lecture started without you.",
            )
    
        draw_navigation_help()
        draw_mobile_controls()
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
