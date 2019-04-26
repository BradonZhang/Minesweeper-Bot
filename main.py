import numpy as np
from PIL import Image, ImageGrab, ImageDraw, ImageFont
# import cv2
import pyautogui as gui
import os
import time
from datetime import datetime

# TODO: Look into logger module
import queue
log = queue.Queue()

# Window coordinates
WIN_X1 = 89
WIN_Y1 = 166
WIN_X2 = 837
WIN_Y2 = 640
WIN_WIDTH = WIN_X2 - WIN_X1
WIN_HEIGHT = WIN_Y2 - WIN_Y1

# Face button coordinates
FACE_WIDTH = 39
FACE_HEIGHT = 39
MIDFACE = int(FACE_WIDTH / 2) # Offsets position to the center of the face
FACE_X1 = 443
FACE_Y1 = 183
FACE_X2 = FACE_X1 + FACE_WIDTH
FACE_Y2 = FACE_Y1 + FACE_HEIGHT

# Board properties
HEIGHT = 16
WIDTH = 30

# Board coordinates
TILE_WIDTH = 24
TILE_HEIGHT = 24
MIDTILE = int(TILE_WIDTH / 2) # Offsets position to the center of the tile
BOARD_X1 = 102
BOARD_Y1 = 242
BOARD_X2 = BOARD_X1 + TILE_WIDTH * WIDTH
BOARD_Y2 = BOARD_Y1 + TILE_HEIGHT * HEIGHT
NUM_MINES = 99
mines_left = NUM_MINES

# numpy array representing an image of the screen
screen = np.array(ImageGrab.grab(bbox=(WIN_X1, WIN_Y1, WIN_X2, WIN_Y2)))

def get_tile_pos(r, c):
    """Retrieves the (x, y) position of a tile
    r -- row of the tile, 0-indexed
    c -- column of the tile, 0-indexed
    """
    x = BOARD_X1 + c * TILE_WIDTH
    y = BOARD_Y1 + r * TILE_HEIGHT
    return (x, y)

def get_sprite(x1, x2, y1, y2):
    """Retrieves a numpy sprite with numpy coordinates given the overall window coordinates"""
    return screen[(y1 - WIN_Y1):(y2 - WIN_Y1), (x1 - WIN_X1):(x2 - WIN_X1), 0:3]

links = []

class Tile:
    """Represents a tile of the Minesweeper board to allow for faster access than screen capture"""
    def __init__(self, r, c):
        self.r, self.c = self.pos = (r, c)
        self.x, self.y = get_tile_pos(self.r, self.c)
        self.value = None
        self.clicked = False
        self.landlocked = False
        self.flagged = False
        self.neighbors = []
        self.links = []
    def __str__(self):
        return f"[{self.value if not self.flagged else 'FLAGGED'}]{self.pos}"
    def toggle_flag(self):
        """Toggles the flagged boolean and records a change in the mines left
        Returns a boolean of the new state of whether the tile is flagged.
        """
        self.flagged = not self.flagged
        global mines_left
        if self.flagged:
            mines_left -= 1
        else:
            mines_left += 1
        return self.flagged
    def click(self, type="left"):
        """Clicks the position of the tile
        type -- the type of click (left/middle/right)
        """
        flagged = (type == "right")
        self.remove_from_links(flagged=flagged)
        click_tile(self.r, self.c, type=type)
    def get_sprite(self):
        """Returns the numpy sprite of the tile"""
        y1 = self.y
        y2 = y1 + TILE_HEIGHT
        x1 = self.x
        x2 = x1 + TILE_WIDTH
        return get_sprite(x1, x2, y1, y2)
    def count_blanks(self):
        """Returns the number of neighbors that are blank tiles"""
        count = 0
        for neighbor in self.neighbors:
            if not neighbor.flagged and neighbor.value is None:
                count += 1
        return count
    def count_flagged(self):
        """Returns the number of neighbors that are flagged tiles"""
        count = 0
        for neighbor in self.neighbors:
            if neighbor.flagged:
                count += 1
        return count
    def create_link(self):
        linked_neighbors = tuple([neighbor for neighbor in self.neighbors if not neighbor.clicked and not neighbor.flagged])
        # TODO: Fix this; it is out of sync and therefore includes neighbors that have been clicked
        new_link = Link(self, self.value - self.count_flagged(), linked_neighbors)
        for neighbor in linked_neighbors:
            neighbor.links.append(new_link)
        links.append(new_link)
    def remove_link(self, link):
        link.remove_tile(self)
        # try:
        #     self.links.remove(link)
        # except:
        #     print(len(self.links))
        #     # Links confuse me...
        # link.tiles.discard(self)
    def remove_from_links(self, flagged=False):
        for link in self.links:
            if link.remove_tile(self):
                if flagged:
                    link.value -= 1
        self.links.clear()

class Link:
    def __init__(self, root, value, *tiles):
        self.root = root
        self.value = value # int for Link, range for RangedLink
        self.tiles = set()
        for tile in tiles[0]:
            self.tiles.add(tile)
    # def __sub__(self, rhs):
    #     if isinstance(rhs, RangedLink):
    #         return RangedLink(range(self.value - rhs.max, self.value - rhs.min + 1), self.tiles - rhs.tiles)
    #     return Link(self.tiles - rhs.tiles)
    #     #this is messy
    def __and__(self, rhs):
        max = min(self.value, rhs.value)
        min = max(self.value - len(self.links - rhs.links),
                  rhs.value - len(rhs.links - self.links))
        return RangedLink(self.root, range(min, max + 1), self.tiles & rhs.tiles)
    def __or__(self, rhs):
        return Link(None, self.value + rhs.value, self.tiles | rhs.tiles)
    # def __xor__(self, rhs):
    #     return self.tiles ^ rhs.tiles
    def __eq__(self, rhs):
        return self.tiles == rhs.tiles
    def __ne__(self, rhs):
        return self.tiles != rhs.tiles
    def __lt__(self, rhs):
        return self.tiles < rhs.tiles
    def __le__(self, rhs):
        return self.tiles <= rhs.tiles
    def __gt__(self, rhs):
        return self.tiles > rhs.tiles
    def __le__(self, rhs):
        return self.tiles >= rhs.tiles
    def __contains__(self, tile):
        return tile in self.tiles
    def __len__(self):
        return len(self.tiles)
    def distance_from(self, other):
        root1 = self.root
        root2 = other.root
        return max(abs(root1.r - root2.r), abs(root1.c - root2.c))
    def get_size(self):
        return len(self.tiles)
    def add_tile(self, tile):
        self.tiles.add(tile)
        tile.links.add(self)
    def remove_tile(self, tile):
        self.tiles.discard(tile)
        # if len(tile.links) == 0:
        #     tile.links.remove(self)
        #     return True
        try:
            tile.links.remove(self)
            return True
        except ValueError:
            return False
            # print(f"Removal of {tile} FAILED with {len(tile.links)}")
    def form_complement(self, link):
        # to_check = self.tiles | link.tiles
        # for tile in to_check:
        #     if tile.flagged or tile.clicked:
        #         tile.remove_from_links(flagged=tile.flagged)
        #         print(f"Removed {tile} from to_check")
        if link.tiles.issubset(self.tiles):
            for tile in link.tiles:
                tile.remove_link(self)
            # self.tiles -= link.tiles
            self.value -= link.value
            return True
        return False
    def is_conclusive(self):
        return self.value == 0 or len(self.tiles) == self.value
    def attempt_click(self):
        """Attempts to click the tiles in the link and returns True if the link should be popped"""
        for tile in self.tiles.copy():
            if tile.flagged:
                self.value -= 1
                if self.value < 0:
                    print("Something isn't right...")
            elif not tile.clicked:
                continue
            self.tiles.discard(tile)
        if len(self.tiles) == 0:
            return True
        if self.is_conclusive():
            type = "right"
            if self.value == 0:
                type = "left"
            num_flagged = self.root.count_flagged()
            log.put(f"LINK CONSIDER {self.root.pos}; SIZE {self.get_size()}; VALUE {self.value}")
            for tile in self.tiles.copy():
                # if not tile.clicked and not tile.flagged:
                print(f"{tile} {type}-clicked (link size: {self.get_size()}, value: {self.value}, flagged: {num_flagged} root: {self.root})!")
                log.put(f"LINK {type[0].upper()}-CLICK {tile.pos}")
                tile.click(type=type)
            return True
                #     clicked = True
                # else:
                #     not_clicked.add(tile)
            # if clicked:
            #     for tile in not_clicked:
            #         print(f"{tile} ignored")
            #         log.put(f"LINK IGNORE {tile.pos}")
            # return clicked
        return False

class RangedLink(Link):
    def __init__(self, root, value, *tiles):
        Link.__init__(root, value, tiles) # value is a range
        self.min = value[0]
        self.max = value[-1]
    def is_conclusive(self):
        return len(self.tiles) == self.min

# Sets up the board of tiles and assigns neighbors
board = np.array([[Tile(i, j) for j in range(WIDTH)] for i in range(HEIGHT)])
for i in range(HEIGHT):
    for j in range(WIDTH):
        tile = board[i, j]
        for r in range(max(0, i - 1), min(HEIGHT, i + 2)):
            for c in range(max(0, j - 1), min(WIDTH, j + 2)):
                if r == i and c == j:
                    continue
                tile.neighbors.append(board[r, c])
print("Board and neighbors set up")

def move_to_tile(r, c):
    """Moves the mouse cursor to a tile
    r -- row of the tile, 0-indexed
    c -- column of the tile, 0-indexed
    """
    x, y = get_tile_pos(r, c)
    gui.moveTo(x + MIDTILE, y + MIDTILE)

def reset_game():
    """Resets the game by clicking the face"""
    gui.click(x = FACE_X1 + MIDFACE, y = FACE_Y1 + MIDFACE)

# Clicks a tile given its row and col, 0-indexed
def click_tile(r, c, type="left"):
    """Clicks a tile
    r -- row of the tile, 0-indexed
    c -- column of the tile, 0-indexed
    type -- the type of click (left/middle/right)
    """
    move_to_tile(r, c)
    # TODO: look into if moving is necessary; consider right/middle click instead
    gui.click(button=type)
    if type == "right":
        if not board[r, c].clicked:
            board[r, c].toggle_flag()
    elif type == "middle":
        for i in range(max(r - 1, 0), min(r + 2, HEIGHT)):
            for j in range(max(c - 1, 0), min(c + 2, WIDTH)):
                if i == r and j == c:
                    continue
                if not board[i, j].flagged:
                    board[i, j].clicked = True
                    board[i, j].remove_from_links()

def get_tile_sprite(r, c):
    """Retrieves the numpy sprite of a tile
    r -- row of the tile, 0-indexed
    c -- column of the tile, 0-indexed
    """
    return board[r, c].get_sprite()

# Dictionary to store images
images = {}
for filename in os.listdir("img"):
    images[os.path.splitext(filename)[0]] = np.array(Image.open(f"img/{filename}"))

def get_game_button():
    """Returns the numpy sprite of the game button"""
    return get_sprite(FACE_X1, FACE_X2, FACE_Y1, FACE_Y2)

def get_game_state():
    """Returns the state of the game, determined by the face sprite
    state  -> return value
    ----------------------
    playing-> 0
    win    -> 1
    lose   -> -1
    """
    face = get_game_button()
    if (np.array_equal(face, images["face_playing"])
        or np.array_equal(face, images["face_await"])
        or np.array_equal(face, images["face_clicked"])):
        return 0
    if np.array_equal(face, images["face_lose"]):
        return -1
    if np.array_equal(face, images["face_win"]):
        return 1
    return 0

def is_playing():
    """Returns a boolean of whether the game is currently playing"""
    return get_game_state() == 0

def is_won():
    """Returns a boolean of whether the game has been won"""
    return get_game_state() == 1

def is_lost():
    """Returns a boolean of whether the game has been lost"""
    return get_game_state() == -1

# Tiles to be considered
# TODO: Consider switching to a linked list
consider = []

def update_board():
    """Updates the board matrix with the new Tile states by reading the screen"""
    added_tiles = []
    for i in range(HEIGHT):
        for j in range(WIDTH):
            tile = board[i, j]
            # Interact with the tile if its state can still change
            if tile.value is None and not tile.flagged:
                sprite = tile.get_sprite()
                if np.array_equal(sprite, images["blank"]):
                    continue
                if np.array_equal(sprite, images["flag"]):
                    tile.toggle_flag()
                    tile.remove_from_links(flagged=True)
                    continue
                # Check the value of the tile, i.e. how many mines are adjacent
                for k in range(9):
                    if np.array_equal(sprite, images[f"tile{k}"]):
                        if k == 0 and np.array_equal(get_game_button(), images["face_await"]):
                            break
                        tile.value = k
                        tile.clicked = True
                        # log.put(f"Registered {tile}")
                        tile.remove_from_links()
                        if k > 0:
                            consider.append(tile)
                            added_tiles.append(tile)
                        break
    for tile in added_tiles:
        tile.create_link()

def do_next_action():
    """Determines the next action to perform, i.e. the next click to make"""
    for i in range(len(consider) - 1, -1, -1):
        tile = consider[i]
        blank_neighbors = 0
        flagged_neighbors = 0
        for neighbor in tile.neighbors:
            if neighbor.flagged:
                flagged_neighbors += 1
            elif not neighbor.clicked:
                blank_neighbors += 1
        if blank_neighbors == 0:
            pass
        # If blanks + flagged = value, flag all remaining
        elif blank_neighbors + flagged_neighbors == tile.value:
            # log.put(f"Rclicked around {tile}; blank={blank_neighbors}, flagged={flagged_neighbors}, len={len(tile.neighbors)}")
            for neighbor in tile.neighbors:
                if not neighbor.clicked and not neighbor.flagged:
                    neighbor.click(type="right")
                    log.put(f"R-CLICK {neighbor.pos}")
        # If flagged = value, open all remaining
        elif flagged_neighbors == tile.value:
            tile.click(type="middle")
            log.put(f"M-CLICK {tile.pos}")
        # When there is insufficient information
        else:
            continue
        consider.pop(i)
        return
    # Implement links
    # return
    for i in range(len(links) - 1, -1, -1):
        if len(links[i].tiles) == 0:
            links.pop(i)
            continue
        # Maybe store links in a dictionary based on their root tile?
        for j in range(i - 1, -1, -1):
            if links[i].distance_from(links[j]) > 2:
                continue
            # links[i].form_complement(links[j])
            if not links[i].form_complement(links[j]):
                links[j].form_complement(links[i])
            # TODO: This can be optimized from O(n^2) to O(n)
            # Check tiles nearby (2 tiles distance between roots) instead of all
        if links[i].attempt_click():
            links.pop(i)
            return
        # if links[i].is_conclusive():
        #     links.pop(i)
            # TODO: This can be optimized; I don't need to check the same boolean
        # TODO: Implement links, check if things are subsets
    # TODO: Implement probability

    # (number of tiles left choose number of mines left possibilities to check)

if is_lost():
    reset_game()
    time.sleep(0.1)
    screen = np.array(ImageGrab.grab(bbox=(WIN_X1, WIN_Y1, WIN_X2, WIN_Y2)))


# Starts withs the tile at row 8, column 15
click_tile(8, 15)

# done = False # Debug option
while is_playing():
    update_board()
    do_next_action()
    # cv2.imshow("Minesweeper", cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))
    # if cv2.waitKey(25) & 0xFF == ord('q'):
    #     cv2.destroyAllWindows()
    #     break
    screen = np.array(ImageGrab.grab(bbox=(WIN_X1, WIN_Y1, WIN_X2, WIN_Y2)))
    # if not done:
    #     done = True
    #     Image.fromarray(board[0, 0].get_sprite()).save("0_0.png")
    #     Image.fromarray(get_game_button()).save("face.png")

# Saves the screen at the end of the game
if is_won():
    dir = "wins"
else:
    dir = "losses"
stop_time = str(datetime.now()).replace(" ", "--").replace(":", "-").split(".")[0]

print(f"{mines_left} MINES LEFT")

final_screen = Image.fromarray(screen)
final_screen.save(f"{dir}/{stop_time}.png")

font_path = "consola.ttf"
hor_font = ImageFont.truetype(font_path, 14)
ver_font = ImageFont.truetype(font_path, 10)
draw = ImageDraw.Draw(final_screen)
hor_text = " ".join([str(i).zfill(2) for i in range(30)])
ver_text = "\n\n".join([str(i).zfill(2) for i in range(16)])
draw.text(xy=(BOARD_X1 - WIN_X1, BOARD_Y1 - WIN_Y1 - round(TILE_HEIGHT * 2 / 3)), text=hor_text, font=hor_font)
draw.text(xy=(BOARD_X1 - WIN_X1 - round(TILE_WIDTH / 2), BOARD_Y1 - WIN_Y1), text=ver_text, font=ver_font)
final_screen.save(f"logs/{stop_time}.png")

for link in links:
    log.put(f"LINK REMAINING ROOTED AT {link.root.pos}; SIZE: {link.get_size()}; VALUE: {link.value}")
    for tile in link.tiles:
        log.put(f"\tTILE: [{tile.value if not tile.flagged else 'FLAGGED'}]{tile.pos}")
with open(f"logs/{stop_time}.log", "a") as f:
    while not log.empty():
        f.write(log.get() + "\n")

"""
TODO:
Make reset() reset the variables as well
Idea: intead of consider list, you should consider non-blank neighbors to blank tiles
record number of mines left

Idea: check before clicking/flagging to see if it fits map

LINKS IDEA:
Links are solved when value = len(tiles) OR when value = 0
In the case of subset: break superset link up into two links (subset and its complement)
In the case of intersection: intersection represents a value of AT MOST the lowest number;
    non-intersection has AT LEAST the complement of that number; if that number = value, then it's a flag

Optimize images: only read center pixel and detect color

CHECK WHY LINKS AREN'T BEING REMOVED PROPERLY
"""
# TODO: for log, add value in the form [value](row, col)
