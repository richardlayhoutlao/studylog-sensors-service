import time

import RPi.GPIO as GPIO

from config import (
    LCD_ADDR,
    LCD_BACKLIGHT,
    LOOP_SLEEP_S,
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
from io_modules.button import ButtonModeToggle
from io_modules.lcd_screen import LCDScreen
from io_modules.rgb_led import RGBLedBlinker
import paho.mqtt.client as mqtt
from random import randrange, uniform
import json
import time

mqttBroker = "test.mosquitto.org"
client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="Studylog")
client.connect(mqttBroker)


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

    lcd_screen = LCDScreen(LCD1602)
    sound_processor = SoundLevelProcessor()

    return led, button, lcd_screen, sound_processor


def _evaluate_discomfort(temp_c, light_pct, sound_pct):
    reasons = []

    if temp_c is not None and temp_c < TEMP_COLD:
        reasons.append(REASON_COLD)
    if temp_c is not None and temp_c > TEMP_HOT:
        reasons.append(REASON_HOT)

    if light_pct < LIGHT_TOO_DARK:
        reasons.append(REASON_DARK)
    if light_pct > LIGHT_TOO_BRIGHT:
        reasons.append(REASON_BRIGHT)

    if sound_pct > SOUND_TOO_LOUD:
        reasons.append(REASON_LOUD)

    return reasons


def run_loop(led, button, lcd_screen, sound_processor):
    while True:
        temp_c = read_temp_c()
        light_raw, light_pct = read_light(ADC, channel=0)
        sound_pct = sound_processor.read_sound_percent(ADC, channel=1)

        reasons = _evaluate_discomfort(temp_c, light_pct, sound_pct)

        is_uncomfortable = len(reasons) > 0
        led.is_uncomfortable = is_uncomfortable

        score = compute_study_score(temp_c, light_pct, sound_pct)
        temp_str = f"{temp_c:0.2f}C" if temp_c is not None else "N/A"

        # LCD
        if button.show_score_mode:
            lcd_screen.show_score(score)
        else:
            lcd_screen.show_stats(temp_str, light_pct, sound_pct,
                                  is_uncomfortable, reasons)
            
            
        # MQTT PUBLISH
        payload = {
            "temperature_score": temp_c,
            "light_score": light_pct,
            "sound_score": sound_pct,
            "score": score,
            "is_uncomfortable": is_uncomfortable,
            "reasons": reasons
        }
        client.publish("Studylog-Richard", json.dumps(payload))
        # TERMINAL OUTPUT
        print(json.dumps(payload))

        time.sleep(LOOP_SLEEP_S)


def destroy(led, button, lcd_screen):
    try:
        button.stop()
    except Exception:
        pass

    try:
        led.stop()
    except Exception:
        pass

    try:
        lcd_screen.clear()
    except Exception:
        pass

    GPIO.cleanup()


def run():
    led = button = lcd_screen = sound_processor = None
    try:
        led, button, lcd_screen, sound_processor = setup()
        run_loop(led, button, lcd_screen, sound_processor)
    except KeyboardInterrupt:
        pass
    finally:
        if led is not None and button is not None and lcd_screen is not None:
            destroy(led, button, lcd_screen)
        else:
            GPIO.cleanup()
