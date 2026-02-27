import importlib.util
import os
import time

import RPi.GPIO as GPIO

from config import (
    LCD_ADDR,
    LCD_BACKLIGHT,
    LOOP_SLEEP_S,
    NEED_CONSEC,
    PCF8591_ADDR,
    REASON_BRIGHT,
    REASON_COLD,
    REASON_DARK,
    REASON_HOT,
    REASON_LOUD,
    LIGHT_TOO_BRIGHT,
    LIGHT_TOO_DARK,
    SOUND_TOO_LOUD,
    TEMP_COLD,
    TEMP_HOT,
)
from drivers import LCD1602
from drivers import PCF8591 as ADC
from utils import compute_study_score
from sensors.light import read_light
from sensors.sound import SoundLevelProcessor
from sensors.temperature import read_temp_c


def _load_io_module(module_name):
    module_path = os.path.join(os.path.dirname(
        __file__), "io", f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_button_module = _load_io_module("button")
_lcd_module = _load_io_module("lcd_ui")
_rgb_module = _load_io_module("rgb_led")

ButtonModeToggle = _button_module.ButtonModeToggle
LCDUI = _lcd_module.LCDUI
RGBLedBlinker = _rgb_module.RGBLedBlinker

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


def setup():
    ADC.setup(PCF8591_ADDR)
    LCD1602.init(LCD_ADDR, LCD_BACKLIGHT)
    LCD1602.clear()

    led = RGBLedBlinker()
    led.start()

    button = ButtonModeToggle()
    button.start()

    lcd_ui = LCDUI(LCD1602)
    sound_processor = SoundLevelProcessor()

    return led, button, lcd_ui, sound_processor


def _evaluate_discomfort(temp_c, light_pct, sound_pct, counters):
    cold_n, hot_n, dark_n, bright_n, loud_n = counters
    reasons = []

    if temp_c is None:
        cold_n = hot_n = 0
    else:
        if temp_c < TEMP_COLD:
            cold_n += 1
            hot_n = 0
        elif temp_c > TEMP_HOT:
            hot_n += 1
            cold_n = 0
        else:
            cold_n = hot_n = 0

    if cold_n >= NEED_CONSEC:
        reasons.append(REASON_COLD)
    if hot_n >= NEED_CONSEC:
        reasons.append(REASON_HOT)

    dark_n = dark_n + 1 if light_pct < LIGHT_TOO_DARK else 0
    bright_n = bright_n + 1 if light_pct > LIGHT_TOO_BRIGHT else 0
    if dark_n >= NEED_CONSEC:
        reasons.append(REASON_DARK)
    if bright_n >= NEED_CONSEC:
        reasons.append(REASON_BRIGHT)

    loud_n = loud_n + 1 if sound_pct > SOUND_TOO_LOUD else 0
    if loud_n >= NEED_CONSEC:
        reasons.append(REASON_LOUD)

    return reasons, (cold_n, hot_n, dark_n, bright_n, loud_n)


def run_loop(led, button, lcd_ui, sound_processor):
    counters = (0, 0, 0, 0, 0)

    while True:
        temp_c = read_temp_c()
        light_raw, light_pct = read_light(ADC, channel=0)
        sound_pct = sound_processor.read_sound_percent(ADC, channel=1)

        reasons, counters = _evaluate_discomfort(
            temp_c, light_pct, sound_pct, counters)

        uncomfortable = len(reasons) > 0
        led.uncomfortable = uncomfortable

        score = compute_study_score(temp_c, light_pct, sound_pct)
        temp_str = f"{temp_c:0.2f}C" if temp_c is not None else "N/A"

        base_line = (
            f"Temp:{temp_str} | Light:{light_raw:3d} ({light_pct:3d}%) | "
            f"Sound:{sound_pct:3d}% | Score:{score:3d}"
        )
        if uncomfortable:
            print(base_line + "  >>> INCONFORT: " + ", ".join(reasons))
        else:
            print(base_line)

        if button.show_score_mode:
            lcd_ui.show_score(score)
        else:
            lcd_ui.show_stats(temp_str, light_pct, sound_pct,
                              uncomfortable, reasons)

        time.sleep(LOOP_SLEEP_S)


def destroy(led, button, lcd_ui):
    try:
        button.stop()
    except Exception:
        pass

    try:
        led.stop()
    except Exception:
        pass

    try:
        lcd_ui.clear()
    except Exception:
        pass

    GPIO.cleanup()


def run():
    led = button = lcd_ui = sound_processor = None
    try:
        led, button, lcd_ui, sound_processor = setup()
        run_loop(led, button, lcd_ui, sound_processor)
    except KeyboardInterrupt:
        pass
    finally:
        if led is not None and button is not None and lcd_ui is not None:
            destroy(led, button, lcd_ui)
        else:
            GPIO.cleanup()
