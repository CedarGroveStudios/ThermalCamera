# Thermal_Cam_v58_PyPortal.py
# 2021-07-07 v5.8
# PyPortal version with Setup helper
# (c) 2021 Cedar Grove Studios

import time
import board
import gc
import busio
import ulab
import displayio
from digitalio import DigitalInOut, Pull, Direction
from simpleio import map_range, tone
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_button import Button
import adafruit_touchscreen
import adafruit_amg88xx
from index_to_rgb.iron_spectrum import index_to_rgb
from thermal_cam_converters import celsius_to_fahrenheit, fahrenheit_to_celsius
from thermal_cam_config import ALARM_F, MIN_RANGE_F, MAX_RANGE_F

"""# For screensave on hold
import adafruit_sdcard
import storage
from   adafruit_bitmapsaver import save_pixels

# Instantiate SD card volume "/sd"
#sd_spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
sd_cs = DigitalInOut(board.SD_CS)  # for PyGamer
sdcard = adafruit_sdcard.SDCard(board.SPI(), sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")"""

gc0 = gc.mem_free()

# Instantiate display and touchscreen
display = board.DISPLAY
ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(board.DISPLAY.width, board.DISPLAY.height),
)

# Load the text font from the fonts folder
font_0 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")

# Establish I2C interface for the AMG8833 Thermal Camera
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
amg8833 = adafruit_amg88xx.AMG88XX(i2c)

# Display spash graphic
with open("/thermal_cam_splash.bmp", "rb") as bitmap_file:
    bitmap = displayio.OnDiskBitmap(bitmap_file)
    splash = displayio.Group(scale=2)
    splash.append(displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter()))
    display.show(splash)
    time.sleep(0.1)  # Allow the splash to display

# Set up ulab arrays
n = 8  # Thermal sensor 'input' array size; the thermal sensor is 8x8
sensor_data = ulab.array(range(n * n)).reshape((n, n))  # Sensor data
grid_data = ulab.zeros(((2 * n) - 1, (2 * n) - 1))  # Array to hold 15x15 data
histogram = ulab.zeros((2 * n) - 1)  # Array to hold histogram accumulation

# Convert default alarm and min/max range values from config file
ALARM_C = fahrenheit_to_celsius(ALARM_F)
MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)

# The board's integral display size and camera orientation
WIDTH = display.width
HEIGHT = display.height
SELFIE = False  # Rear camera view; True for front camera

GRID_AXIS = (2 * n) - 1  # Number of cells along the grid x or y axis
GRID_SIZE = HEIGHT  # Set to maximum number of pixels for a square grid
GRID_X_OFFSET = WIDTH - GRID_SIZE  # Right-align grid with display boundary
CELL_SIZE = GRID_SIZE // GRID_AXIS  # Size of a grid cell in pixels

PALETTE_SIZE = 100  # Number of colors in spectral palette (cannot be <= 0)

# Default colors for non-grid display elements
BLACK = 0x000000
RED = 0xFF0000
YELLOW = 0xFFFF00
CYAN = 0x00FFFF
BLUE = 0x0000FF
WHITE = 0xFFFFFF

# Text colors for setup method's on-screen parameters
param_colors = [("ALARM", WHITE), ("RANGE", RED), ("RANGE", CYAN)]

# ### Helpers ###
def play_tone(freq=440, duration=0.01):
    tone(board.A0, freq, duration)


def flash_status(text="", duration=0.05):  # Flash status message once
    status_label.color = WHITE
    status_label.text = text
    time.sleep(duration)
    status_label.color = BLACK
    time.sleep(duration)
    status_label.text = ""
    return


def spectrum():  # Load a test spectrum into the grid_data array
    for row in range(0, GRID_AXIS):
        for col in range(0, GRID_AXIS):
            grid_data[row][col] = ((row * GRID_AXIS) + col) * 1 / 235
    return


def update_image_frame(selfie=False):  # Get camera data and update display
    for row in range(0, GRID_AXIS):
        for col in range(0, GRID_AXIS):
            if selfie:
                color_index = grid_data[GRID_AXIS - 1 - row][col]
            else:
                color_index = grid_data[GRID_AXIS - 1 - row][GRID_AXIS - 1 - col]
            color = index_to_rgb(round(color_index * PALETTE_SIZE, 0) / PALETTE_SIZE)
            if color != image_group[((row * GRID_AXIS) + col)].fill:
                image_group[((row * GRID_AXIS) + col)].fill = color
    return


def update_histo_frame():  # Calculate and display histogram
    min_histo.text = str(MIN_RANGE_F)  # Display histogram legend
    max_histo.text = str(MAX_RANGE_F)

    histogram = ulab.zeros(GRID_AXIS)  # Clear histogram accumulation array
    for row in range(0, GRID_AXIS):  # Collect camera data and calculate histo
        for col in range(0, GRID_AXIS):
            histo_index = int(map_range(grid_data[col, row], 0, 1, 0, GRID_AXIS - 1))
            histogram[histo_index] = histogram[histo_index] + 1

    histo_scale = ulab.numerical.max(histogram) / (GRID_AXIS - 1)
    if histo_scale <= 0:
        histo_scale = 1

    for col in range(0, GRID_AXIS):  # Display histogram
        for row in range(0, GRID_AXIS):
            if histogram[col] / histo_scale > GRID_AXIS - 1 - row:
                image_group[((row * GRID_AXIS) + col)].fill = index_to_rgb(
                    round((col / GRID_AXIS), 3)
                )
            else:
                image_group[((row * GRID_AXIS) + col)].fill = BLACK
    return


def ulab_bilinear_interpolation():  # 2x bilinear interpolation
    # Upscale sensor data array; by @v923z and @David.Glaude
    grid_data[1::2, ::2] = sensor_data[:-1, :]
    grid_data[1::2, ::2] += sensor_data[1:, :]
    grid_data[1::2, ::2] /= 2
    grid_data[::, 1::2] = grid_data[::, :-1:2]
    grid_data[::, 1::2] += grid_data[::, 2::2]
    grid_data[::, 1::2] /= 2
    return


def read_buttons():
    button_pressed = None
    touch = ts.touch_point
    if touch:
        for button in buttons:
            if button.contains(touch):
                button.selected = True
                play_tone(1319, 0.030)  # E6
                button_pressed = button.name
                while ts.touch_point:
                    time.sleep(0.1)
                button.selected = False
    return button_pressed


def setup_mode():  # Set alarm threshold and minimum/maximum range values
    mode_button.label = "UP"
    focus_button.label = "DOWN"
    status_label.color = WHITE
    status_label.text = "-SELECT-"

    ave_label.color = BLACK  # Turn off average label and value display
    ave_value.color = BLACK

    max_value.text = str(MAX_RANGE_F)  # Display maximum range value
    min_value.text = str(MIN_RANGE_F)  # Display minimum range value

    param_index = 0  # Reset index of parameter to set
    setup_state = True

    while setup_state:
        # Select parameter to set
        setup_param_state = True
        while setup_state and setup_param_state:
            button_pressed = read_buttons()
            if button_pressed == "setup":
                setup_state = False
            elif button_pressed == "hold":
                setup_param_state = False
            else:
                if button_pressed == "mode":  # up
                    param_index = param_index - 1
                if button_pressed == "focus":  # down
                    param_index = param_index + 1
                param_index = max(0, min(2, param_index))
                image_group[param_index + 226].color = BLACK
                time.sleep(0.05)
                image_group[param_index + 226].color = param_colors[param_index][1]
                time.sleep(0.2)

        # Adjust parameter value
        setup_value_state = True
        while setup_state and setup_value_state:
            param_value = int(image_group[param_index + 230].text)
            button_pressed = read_buttons()
            if button_pressed == "setup":
                setup_state = False
            elif button_pressed == "hold":
                setup_value_state = False
            else:
                if button_pressed == "mode":  # up
                    param_value = param_value + 1
                if button_pressed == "focus":  # down
                    param_value = param_value - 1
                param_value = max(32, min(157, param_value))
                image_group[param_index + 230].text = str(param_value)
                image_group[param_index + 230].color = BLACK
                time.sleep(0.05)
                image_group[param_index + 230].color = param_colors[param_index][1]
                time.sleep(0.2)

    if not display_image:
        mode_button.label = "IMAGE"
    else:
        mode_button.label = "HISTO"
    if not display_focus:
        focus_button.label = "FOCUS"
    else:
        focus_button.label = "ORIG"
    flash_status("RESUME", 0.5)

    # Display average label and value
    ave_label.color = YELLOW
    ave_value.color = YELLOW
    return int(alarm_value.text), int(max_value.text), int(min_value.text)


play_tone(440, 0.1)  # A4
play_tone(880, 0.1)  # A5

# ### Define the display group ###
t0 = time.monotonic()
image_group = displayio.Group()

# Define the foundational thermal image grid cells; image_group[0:224]
#   image_group[#]=(row * GRID_AXIS) + column
for row in range(0, GRID_AXIS):
    for col in range(0, GRID_AXIS):
        cell_x = (col * CELL_SIZE) + GRID_X_OFFSET
        cell_y = row * CELL_SIZE
        cell = Rect(
            x=cell_x,
            y=cell_y,
            width=CELL_SIZE,
            height=CELL_SIZE,
            fill=None,
            outline=None,
            stroke=0,
        )
        image_group.append(cell)

# Define labels and values
status_label = Label(font_0, text="", color=None, max_glyphs=6)
status_label.anchor_point = (0.5, 0.5)
status_label.anchored_position = ((WIDTH // 2) + (GRID_X_OFFSET // 2), HEIGHT // 2)
image_group.append(status_label)

alarm_label = Label(font_0, text="alarm", color=WHITE, max_glyphs=5)
alarm_label.anchor_point = (0, 0)
alarm_label.anchored_position = (10, 26)
image_group.append(alarm_label)

max_label = Label(font_0, text="max", color=RED, max_glyphs=3)
max_label.anchor_point = (0, 0)
max_label.anchored_position = (10, 56)
image_group.append(max_label)

min_label = Label(font_0, text="min", color=CYAN, max_glyphs=3)
min_label.anchor_point = (0, 0)
min_label.anchored_position = (10, 116)
image_group.append(min_label)

ave_label = Label(font_0, text="ave", color=YELLOW, max_glyphs=3)
ave_label.anchor_point = (0, 0)
ave_label.anchored_position = (10, 86)
image_group.append(ave_label)

alarm_value = Label(font_0, text=str(ALARM_F), color=WHITE, max_glyphs=3)
alarm_value.anchor_point = (0, 0)
alarm_value.anchored_position = (10, 15)
image_group.append(alarm_value)

max_value = Label(font_0, text=str(MAX_RANGE_F), color=RED, max_glyphs=3)
max_value.anchor_point = (0, 0)
max_value.anchored_position = (10, 45)
image_group.append(max_value)

min_value = Label(font_0, text=str(MIN_RANGE_F), color=CYAN, max_glyphs=3)
min_value.anchor_point = (0, 0)
min_value.anchored_position = (10, 105)
image_group.append(min_value)

ave_value = Label(font_0, text="---", color=YELLOW, max_glyphs=3)
ave_value.anchor_point = (0, 0)
ave_value.anchored_position = (10, 75)
image_group.append(ave_value)

min_histo = Label(font_0, text="", color=None, max_glyphs=3)
min_histo.anchor_point = (0, 0.5)
min_histo.anchored_position = (5 + GRID_X_OFFSET, HEIGHT - 10)
image_group.append(min_histo)

max_histo = Label(font_0, text="", color=None, max_glyphs=3)
max_histo.anchor_point = (1, 0.5)
max_histo.anchored_position = (WIDTH - 7, HEIGHT - 10)
image_group.append(max_histo)

range_histo = Label(font_0, text="", color=None, max_glyphs=7)
range_histo.anchor_point = (0.5, 0.5)
range_histo.anchored_position = ((WIDTH // 2) + (GRID_X_OFFSET // 2), HEIGHT - 10)
image_group.append(range_histo)

# -- BUTTONS -- #
buttons = []
mode_button = Button(
    x=10,
    y=145,
    height=40,
    width=60,
    style=Button.ROUNDRECT,
    fill_color=None,
    outline_color=BLUE,
    name="mode",
    label="HISTO",
    label_font=font_0,
    label_color=CYAN,
    selected_fill=BLUE,
    selected_outline=WHITE,
)
image_group.append(mode_button)
buttons.append(mode_button)

focus_button = Button(
    x=10,
    y=190,
    height=40,
    width=60,
    style=Button.ROUNDRECT,
    fill_color=None,
    outline_color=BLUE,
    name="focus",
    label="FOCUS",
    label_font=font_0,
    label_color=CYAN,
    selected_fill=BLUE,
    selected_outline=WHITE,
)
image_group.append(focus_button)
buttons.append(focus_button)

hold_button = Button(
    x=GRID_X_OFFSET,
    y=0,
    height=GRID_SIZE,
    width=GRID_SIZE,
    style=Button.RECT,
    fill_color=None,
    outline_color=BLACK,
    name="hold",
    selected_fill=None,
    selected_outline=CYAN,
)
image_group.append(hold_button)
buttons.append(hold_button)

setup_button = Button(
    x=0,
    y=0,
    height=140,
    width=WIDTH - GRID_SIZE,
    style=Button.RECT,
    fill_color=None,
    outline_color=BLACK,
    name="setup",
    selected_fill=None,
    selected_outline=BLACK,
)
image_group.append(setup_button)
buttons.append(setup_button)

t1 = time.monotonic()
# ###--- PRIMARY PROCESS SETUP ---###
display_image = True  # Image display mode default; False for histogram
display_hold = False  # Active display mode default; True to hold display
display_focus = False  # Standard display range default; True for range focus
orig_max_range_f = MAX_RANGE_F  # There are no initial original range values
orig_min_range_f = MIN_RANGE_F

# Activate display and play welcome tone
display.show(image_group)
spectrum()
update_image_frame()
flash_status("IRON SPECTRUM", 0.75)
play_tone(880, 0.010)

###--- PRIMARY PROCESS LOOP ---###
while True:
    t2 = t3 = time.monotonic()
    if display_hold:
        flash_status("-HOLD-", 0.25)
    else:
        sensor = amg8833.pixels  # Get camera data

    sensor_data = ulab.array(sensor)
    for row in range(0, 8):  # Constrain sensor values to valid range
        for col in range(0, 8):
            sensor_data[col, row] = min(max(sensor_data[col, row], 0), 80)

    t4 = time.monotonic()
    # Display alarm setting and max, min, and ave
    v_max = ulab.numerical.max(sensor_data)  # Update maximum value
    v_min = ulab.numerical.min(sensor_data)  # Update minimum value
    v_ave = ulab.numerical.mean(sensor_data)  # Update average value

    alarm_value.text = str(ALARM_F)  # required if setup helper is used
    max_value.text = str(celsius_to_fahrenheit(v_max))
    min_value.text = str(celsius_to_fahrenheit(v_min))
    ave_value.text = str(celsius_to_fahrenheit(v_ave))

    t5 = time.monotonic()
    # normalize temperature values to index and interpolate
    sensor_data = (sensor_data - MIN_RANGE_C) / (MAX_RANGE_C - MIN_RANGE_C)
    grid_data[::2, ::2] = sensor_data  # Copy sensor data to the grid array
    ulab_bilinear_interpolation()  # Interpolate and produce 15x15 result

    # Display image or histogram
    t6 = time.monotonic()
    if display_image:
        update_image_frame(selfie=SELFIE)
    else:
        update_histo_frame()

    # Play alarm note if alarm threshold is exceeded
    if v_max >= ALARM_C:
        play_tone(1220, 0.015)
        flash_status("-ALARM-", 0.2)
        pass

    button_pressed = read_buttons()
    if button_pressed == "hold":  # Toggle display hold (shutter)
        display_hold = not display_hold
        if display_hold:
            # save_pixels('/sd/display_capture.bmp', display)  # capture image of display
            pass

    if button_pressed == "mode":  # Toggle image/histogram mode (display mode)
        if display_image:
            mode_button.label = "IMAGE"
            range_histo.text = "-RANGE-"
            min_histo.color = CYAN
            max_histo.color = RED
            range_histo.color = BLUE
        else:
            mode_button.label = "HISTO"
            min_histo.color = None
            max_histo.color = None
            range_histo.color = None
        display_image = not display_image

    if button_pressed == "focus":  # toggle focus mode (display focus)
        if display_focus:
            MIN_RANGE_F = orig_min_range_f  # restore previous (original) range values
            MAX_RANGE_F = orig_max_range_f
            # update range min and max values in Celsius
            MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
            MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)
            flash_status("ORIG", 0.2)
            focus_button.label = "FOCUS"
        else:
            orig_min_range_f = MIN_RANGE_F  # set range values to image min/max
            orig_max_range_f = MAX_RANGE_F
            MIN_RANGE_F = celsius_to_fahrenheit(v_min)
            MAX_RANGE_F = celsius_to_fahrenheit(v_max)
            MIN_RANGE_C = v_min  # update range temp in Celsius
            MAX_RANGE_C = v_max  # update range temp in Celsius
            flash_status("FOCUS", 0.2)
            focus_button.label = "ORIG"
        display_focus = not display_focus

    if button_pressed == "setup":  # Setup mode selected (setup)
        flash_status("SETUP", 0.5)
        # Invoke startup helper; update alarm and range values
        ALARM_F, MAX_RANGE_F, MIN_RANGE_F = setup_mode()
        ALARM_C = fahrenheit_to_celsius(ALARM_F)
        MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
        MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)

    t7 = time.monotonic()
    print("---PyPortal")
    print("define displayio      ", round(t1 - t0, 3))
    print("data acq time, acq/sec", round(t4 - t3, 3), round(1 / (t4 - t3), 3))
    print("update display stats  ", round(t5 - t4, 3))
    print("interpolation         ", round(t6 - t5, 3))
    print("update display time   ", round(t7 - t6, 3))
    print("frame time, frames/sec", round(t7 - t2, 3), round(1 / (t7 - t2), 3))
    print("free memory", gc.mem_free(), gc0)
