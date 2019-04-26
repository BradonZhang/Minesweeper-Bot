import numpy as np
from PIL import Image, ImageGrab
import cv2
import pyautogui as gui
import os

# Necessary coordinates and dimensions
WIN_X1 = 104 + 12
WIN_Y1 = 166
WIN_X2 = 347 + 12
WIN_Y2 = 473
WIN_WIDTH = WIN_X2 - WIN_X1
WIN_HEIGHT = WIN_Y2 - WIN_Y1
FACE_WIDTH = 39
FACE_HEIGHT = 39
MIDFACE = int(FACE_WIDTH / 2) # Offsets position to the center of the face
FACE_X1 = 206 + 12
FACE_Y1 = 183
FACE_X2 = FACE_X1 + FACE_WIDTH
FACE_Y2 = FACE_Y1 + FACE_HEIGHT
MIDTILE_X, MIDTILE_Y = 225 + 12, 350

# numpy array representing an image of the screen
screen = np.array(ImageGrab.grab(bbox=(WIN_X1, WIN_Y1, WIN_X2, WIN_Y2)))

def get_sprite(x1, x2, y1, y2):
    """Retrieves a numpy sprite with numpy coordinates given the overall window coordinates"""
    return screen[(y1 - WIN_Y1):(y2 - WIN_Y1), (x1 - WIN_X1):(x2 - WIN_X1), 0:3]

def reset_game():
    """Resets the game by clicking the face"""
    gui.click(x = FACE_X1 + MIDFACE, y = FACE_Y1 + MIDFACE)

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

# done = False # Debug option
while not is_won():
    reset_game()
    gui.click(x = MIDTILE_X, y = MIDTILE_Y)
    cv2.imshow("Minesweeper", cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))
    if cv2.waitKey(25) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        break
    screen = np.array(ImageGrab.grab(bbox=(WIN_X1, WIN_Y1, WIN_X2, WIN_Y2)))
    # if not done:
    #     done = True
    #     Image.fromarray(board[0, 0].get_sprite()).save("0_0.png")
    #     Image.fromarray(get_game_button()).save("face.png")
