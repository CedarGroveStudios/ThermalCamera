# Thermal_Cam_v56_miniTFT_Wing.py
# 2021-06-04 v5.6
# mini TFT FeatherWing version
# (c) 2021 Cedar Grove Studios

import time
import board
import gc
import busio
import ulab
import displayio
import neopixel
from digitalio import DigitalInOut, Pull, Direction
from simpleio import map_range, tone
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
import adafruit_amg88xx
from index_to_rgb.iron_spectrum import index_to_rgb
from thermal_cam_converters import celsius_to_fahrenheit, fahrenheit_to_celsius
from thermal_cam_config import ALARM_F, MIN_RANGE_F, MAX_RANGE_F

from adafruit_featherwing import minitft_featherwing

gc0 = gc.mem_free()

# Release any resources currently in use and instatiate display
displayio.release_displays()
minitft = minitft_featherwing.MiniTFTFeatherWing()
display = minitft.display

# Load the text font from the fonts folder
font_0 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")

# Establish I2C interface for the AMG8833 Thermal Camera
i2c = board.I2C()
amg8833 = adafruit_amg88xx.AMG88XX(i2c)

# Define control buttons; Focus, Hold, Image/Histogram

# Setup neopixel
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
pixel[0] = 0x0F000F

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
# param_list = [("ALARM", WHITE), ("RANGE", RED), ("RANGE", CYAN)]

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

# Define labels and values using element grid coordinates
status_label = Label(font_0, text="", color=None, max_glyphs=6)
status_label.anchor_point = (0.5, 0.5)
status_label.anchored_position = ((WIDTH // 2) + (GRID_X_OFFSET // 2), HEIGHT // 2)
image_group.append(status_label)  # image_group[65]225

alarm_label = Label(font_0, text="alarm", color=WHITE, max_glyphs=5)
alarm_label.anchor_point = (0, 0)
alarm_label.anchored_position = (10, 9)
image_group.append(alarm_label)  # image_group[66]226

max_label = Label(font_0, text="max", color=RED, max_glyphs=3)
max_label.anchor_point = (0, 0)
max_label.anchored_position = (10, 29)
image_group.append(max_label)  # image_group[67]227

min_label = Label(font_0, text="min", color=CYAN, max_glyphs=3)
min_label.anchor_point = (0, 0)
min_label.anchored_position = (10, 69)
image_group.append(min_label)  # image_group[68]228

ave_label = Label(font_0, text="ave", color=YELLOW, max_glyphs=3)
ave_label.anchor_point = (0, 0)
ave_label.anchored_position = (10, 49)
image_group.append(ave_label)  # image_group[69]229

alarm_value = Label(font_0, text=str(ALARM_F), color=WHITE, max_glyphs=3)
alarm_value.anchor_point = (0, 0)
alarm_value.anchored_position = (10, 0)
image_group.append(alarm_value)  # image_group[70]230

max_value = Label(font_0, text=str(MAX_RANGE_F), color=RED, max_glyphs=3)
max_value.anchor_point = (0, 0)
max_value.anchored_position = (10, 20)
image_group.append(max_value)  # image_group[71]231

min_value = Label(font_0, text=str(MIN_RANGE_F), color=CYAN, max_glyphs=3)
min_value.anchor_point = (0, 0)
min_value.anchored_position = (10, 60)
image_group.append(min_value)  # image_group[72]232

ave_value = Label(font_0, text="---", color=YELLOW, max_glyphs=3)
ave_value.anchor_point = (0, 0)
ave_value.anchored_position = (10, 40)
image_group.append(ave_value)  # image_group[73]233

min_histo = Label(font_0, text="", color=None, max_glyphs=3)
min_histo.anchor_point = (0, 0.5)
min_histo.anchored_position = (5 + GRID_X_OFFSET, HEIGHT - 10)
image_group.append(min_histo)  # image_group[74]234

max_histo = Label(font_0, text="", color=None, max_glyphs=3)
max_histo.anchor_point = (1, 0.5)
max_histo.anchored_position = (WIDTH - 7, HEIGHT - 10)
image_group.append(max_histo)  # image_group[75]235

range_histo = Label(font_0, text="", color=None, max_glyphs=7)
range_histo.anchor_point = (0.5, 0.5)
range_histo.anchored_position = ((WIDTH // 2) + (GRID_X_OFFSET // 2), HEIGHT - 10)
image_group.append(range_histo)  # image_group[76]236

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
flash_status("IRON", 0.75)
play_tone(880, 0.010)

# ###--- PRIMARY PROCESS LOOP ---###
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

    # Toggle shutter (display hold)
    buttons = minitft.buttons
    if buttons.select:
        play_tone(1319, 0.030)  # E6
        flash_status("-HOLD-")
        display_hold = not display_hold

        while buttons.select:
            buttons = minitft.buttons
            time.sleep(0.25)

    # Toggle image/histogram mode (display mode)
    buttons = minitft.buttons
    if buttons.b:
        play_tone(1319, 0.030)  # E6
        while buttons.b:
            buttons = minitft.buttons
            time.sleep(0.25)

        if display_image:
            flash_status("-HISTO-", 0.5)
            range_histo.text = "-RANGE-"
            min_histo.color = CYAN
            max_histo.color = RED
            range_histo.color = BLUE
        else:
            flash_status("-IMAGE-", 0.5)
            min_histo.color = None
            max_histo.color = None
            range_histo.color = None
        display_image = not display_image

    # Toggle focus mode (display focus)
    buttons = minitft.buttons
    if buttons.a:
        play_tone(698, 0.030)  # F5
        if display_focus:
            MIN_RANGE_F = orig_min_range_f  # restore original range values
            MAX_RANGE_F = orig_max_range_f
            # update range min and max values in Celsius
            MIN_RANGE_C = fahrenheit_to_celsius(MIN_RANGE_F)
            MAX_RANGE_C = fahrenheit_to_celsius(MAX_RANGE_F)
            flash_status("-ORIG-", 0.5)
        else:
            orig_min_range_f = MIN_RANGE_F  # set range values to image min/max
            orig_max_range_f = MAX_RANGE_F
            MIN_RANGE_C = v_min  # update range temp in Celsius
            MAX_RANGE_C = v_max  # update range temp in Celsius
            MIN_RANGE_F = celsius_to_fahrenheit(MIN_RANGE_C) - 1
            MAX_RANGE_F = celsius_to_fahrenheit(MAX_RANGE_C) + 1

            flash_status("-FOCUS-", 0.5)
        display_focus = not display_focus

        while buttons.a:
            buttons = minitft.buttons
            time.sleep(0.25)

    t7 = time.monotonic()
    print("---miniTFT FeatherWing/")
    print("define displayio      ", round(t1 - t0, 3))
    print("data acq time, acq/sec", round(t4 - t3, 3), round(1 / (t4 - t3), 3))
    print("update display stats  ", round(t5 - t4, 3))
    print("interpolation         ", round(t6 - t5, 3))
    print("update display time   ", round(t7 - t6, 3))
    print("frame time, frames/sec", round(t7 - t2, 3), round(1 / (t7 - t2), 3))
    print("free memory", gc.mem_free(), gc0)
