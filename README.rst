Introduction
============




.. image:: https://img.shields.io/discord/327254708534116352.svg
    :target: https://adafru.it/discord
    :alt: Discord


.. image:: https://github.com/CedarGroveStudios/ThermalCamera/workflows/Build%20CI/badge.svg
    :target: https://github.com/CedarGroveStudios/ThermalCamera/actions
    :alt: Build Status


.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

A PyGamer/PyBadge thermal imaging tool.

.. image:: https://github.com/CedarGroveStudios/ThermalCamera/blob/main/media/graphics/DSC06005a.jpg
  :width: 500
  :alt: PyGamer Thermal Camera

The Thermal Camera is a portable AMG8833-based thermopile array imager device
implemented using CircuitPython on an Adafruit PyGamer or PyBadge SAMD51 handheld
gaming platform.

Features include measurement and imaging of 225 discrete temperatures within the
range of 0 to 80 degrees Celsius, adjustable color display gradient range,
settable alarm threshold with audible alarm, image snapshot, image and histogram
display modes, and an automatic temperature range focus option. The
PyGamer/PyBadge platform provides the color display, control buttons, a speaker
for the audible alarm (https://www.adafruit.com/product/4227), and room for a
LiPo rechargeable battery (https://www.adafruit.com/product/4237).

This implementation uses the Adafruit AMG8833 Thermal Camera FeatherWing
(https://www.adafruit.com/product/3622). The breakout board version of the
camera (https://www.adafruit.com/product/3538) could be used via the Stemma
interface in cases where the camera is mounted independently of the
PyGamer/PyBadge unit.

Refer to the Adafruit Learning Guide's assembly instructions and downloadable
code are available in the *Improved AMG8833 PyGamer Thermal Camera Learning Guide*:
(https://learn.adafruit.com/improved-amg8833-pygamer-thermal-camera).

Project Description
===================

A section of exhaust duct for the clothes dryer in our late 1940s-era home seemed to be prone to developing obstructions. It's scheduled to be replaced in a couple of months, but until it is, we'll keep a pretty close eye on it and clean it often. This project evolved from the need to watch for abnormal temperature build-up along the problematic two-meter section of exhaust duct.

The first exhaust duct monitor designs used thermistors (eventually thermocouples) connected to an Adafruit Feather M4 Express for data collection and analysis. Code was to be be written in CircuitPython. Some graphic visualization would be nice as would a wireless IoT approach, but monitoring with a local audible alarm was more important.

As the project design developed, the AMG8833 8x8 thermopile array sensor and its imaging capability became more desirable. Not only did the sensor match the needed temperature range, it provided the capability to measure many points along the duct rather than only three. Also, the sensor could be mounted in a convenient location a distance away from the duct and still perform the needed measurements. There was also no need to string wires and physically mount thermocouples to the ductwork.

It first appeared that CircuitPython may not be fast enough to process the AMG8833 matrix data for real-time graphical imaging, but would only be responsive when conducting simple numerical calculations (like alarm threshold detection) on the matrix data. Since a ten-second measurement interval was fast enough for this project, evolving the design to include a graphical image display was seen as a possibility in spite of those perceived limitations. After some initial prototype tests, it was found that CircuitPython and the DisplayIO library were indeed fast enough and could provide a measurement interval of less than one second per frame of 64 measurements.

The design evolved from the initial prototype tests to a final version that met the original requirements, but also had added features that allowed the unit to be used as a standalone, camera-like device. The code was modified to work with the PyBadge or PyGamer, adjusting for direction buttons or joystick operation. After final testing, a friend referred to the Thermal Camera as being similar to and as useful as a carpentry stud finder.

Test video: https://youtu.be/IyMZOlKJu3Q

In addition to Adafruit libraries, the Thermal Camera utilizes a number of PyGamer/PyBadge-stored files and conversion helpers in order to operate:
 -  ``thermalcamera_code.py`` (renamed to code.py), the primary code module compatible with CircuitPython 8.0.0, stored in the root directory
 -  ``thermalcamera_config.py``, a Python-formatted list of default operating parameters, stored in the root directory
 -  ``thermalcamera_splash.bmp``, a bitmapped graphics file used for the opening splash screen, stored in the root directory
 -  ``OpenSans-9.bdf``, a sans serif font file, stored in the ``fonts`` folder
 -  ``thermalcamera_converters.py``, helpers for temperature conversion, stored in the root directory
 -  The ``iron.py`` spectrum helper, stored in the ``index_to_rgb`` folder (from CedarGroveStudios/CircuitPython_RGB_SpectrumTools and Adafruit/CircuitPython_Community_Bundle)

Primary Project Objectives
==========================

Required:
 1) Continuously monitor and detect abnormal temperatures along a two-meter section of clothes dryer exhaust duct with a minimum sampling rate of one series of measurements per ten seconds.
 2) Monitor and detect a minimum of three data points (duct entry, middle, and end sections). The minimum temperature monitoring range is from typical room temperature to ten degrees Celsius above the maximum safe operating temperature. Typical accuracy of +/-2.5 degrees C is sufficient. The alarm threshold is set by a default start-up configuration file and manually through the device user interface.
 3) An alarm condition activates a locally-placed and distinctive audible alarm signal that continuously sounds until the high temperature drops to a safe level.
 4) The exhaust duct temperature measurements will be displayed in easy to read numerals, defaulting to degrees Fahrenheit.
 5) The device is powered by a wall-mounted USB power supply that provides primary operating power and charging of the device's internal backup battery. Battery backup duration is one-hour minimum.
 6) Utilize CircuitPython for the software implementation.

Optional (for future versions):
 1) Graphical temperature display that includes a representative image, histogram, and trends.
 2) Image view: 45 to 60-degree field of view over 5-meter minimum imaging range.
 3) Hold measurements for analysis.
 4) Interactive minimum and maximum display range settings.
 5) Record and retain monitoring history for up to two hours. Display historical data or create file for external analysis.
 6) Selectable Celsius or Fahrenheit numerical display.
 7) Selectable display color spectrum. The ``index_to_rgb`` folder already contains helpers for the visible and grayscale spectrums.

.. image:: https://github.com/CedarGroveStudios/ThermalCamera/blob/main/media/graphics/performance_frame_rate.png
  :width: 400
  :alt: Thermal Camera Performance Statistics

.. image:: https://github.com/CedarGroveStudios/ThermalCamera/blob/main/media/graphics/AMG8833_TC_Perf_Comparison.png
  :width: 800
  :alt: MPU Performance Comparison

Dependencies
=============
This project depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_

* `Adafruit PyGamer <https://www.adafruit.com/product/4242>`_

* `Adafruit PyBadge <https://www.adafruit.com/product/4200>`_


Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.
