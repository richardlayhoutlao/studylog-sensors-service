#!/usr/bin/env python3
import time
import threading
import random

import PCF8591 as ADC
import RPi.GPIO as GPIO
import LCD1602

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ----------------- Button (thread, no edge) -----------------
BtnPin = 23
GPIO.setup(BtnPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

stop_button = False
show_score_mode = False  # False = stats, True = Study Environment Score

def button_loop():
    global stop_button, show_score_mode
    last = GPIO.input(BtnPin)

    while not stop_button:
        current = GPIO.input(BtnPin)

        # falling edge: 1 -> 0 means pressed (pull-up)
        if current == 0 and last == 1:
            show_score_mode = not show_score_mode
            print("Pressed -> mode:", "SCORE" if show_score_mode else "STATS")
            time.sleep(0.2)  # debounce

        last = current
        time.sleep(0.03)

# ----------------- Helpers -----------------
def pad16(text: str) -> str:
    return (text + " " * 16)[:16]

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def read_stable(channel: int, samples: int = 4, delay: float = 0.0008) -> int:
    total = 0
    for _ in range(samples):
        ADC.read(channel)
        val = ADC.read(channel)
        total += val
        time.sleep(delay)
    return total // samples

def map_range_to_percent(x, x_min, x_max):
    if x_max == x_min:
        return 0
    x = clamp(x, x_min, x_max)
    return int((x - x_min) * 100 / (x_max - x_min))

# ----------------- DS18B20 -----------------
DS18B20_ID = "28-012037a4749a"

def read_temp_c():
    try:
        with open(f"/sys/bus/w1/devices/{DS18B20_ID}/w1_slave", "r") as f:
            lines = f.read().splitlines()
        if not lines or "YES" not in lines[0]:
            return None
        return float(lines[1].split("t=")[1]) / 1000.0
    except:
        return None

# ----------------- RGB LED -----------------
LED_R = 17
LED_G = 18
LED_B = 28

LED_COMMON_ANODE = True  # keep True if your RGB LED is common anode

p_R = p_G = p_B = None
_led_lock = threading.Lock()

def led_setup():
    global p_R, p_G, p_B
    for pin in (LED_R, LED_G, LED_B):
        GPIO.setup(pin, GPIO.OUT)

    p_R = GPIO.PWM(LED_R, 2000)
    p_G = GPIO.PWM(LED_G, 2000)
    p_B = GPIO.PWM(LED_B, 2000)

    p_R.start(0)
    p_G.start(0)
    p_B.start(0)
    led_off()

def _apply_pwm(pwm, val_0_100):
    val_0_100 = clamp(val_0_100, 0, 100)
    if LED_COMMON_ANODE:
        pwm.ChangeDutyCycle(100 - val_0_100)
    else:
        pwm.ChangeDutyCycle(val_0_100)

def led_set_rgb(r, g, b):
    with _led_lock:
        _apply_pwm(p_R, r)
        _apply_pwm(p_G, g)
        _apply_pwm(p_B, b)

def led_off():
    led_set_rgb(0, 0, 0)

# ----------------- LED Blinker Thread -----------------
BLINK_ON  = 0.1
BLINK_OFF = 0.1

uncomfortable_flag = False
stop_blinker = False

def blinker_loop():
    global uncomfortable_flag, stop_blinker
    on = False
    while not stop_blinker:
        if uncomfortable_flag:
            # blink RED when uncomfortable
            on = not on
            if on:
                led_set_rgb(100, 0, 0)
                time.sleep(BLINK_ON)
            else:
                led_off()
                time.sleep(BLINK_OFF)
        else:
            led_set_rgb(0, 100, 0)
            time.sleep(0.05)

# ----------------- Score (placeholder random) -----------------
def compute_study_score(temp_c, light_pct, sound_pct):
    return random.randint(0, 100)

# ----------------- Main -----------------
def setup():
    ADC.setup(0x48)
    LCD1602.init(0x27, 1)
    LCD1602.clear()
    led_setup()

    t_led = threading.Thread(target=blinker_loop, daemon=True)
    t_led.start()

    t_btn = threading.Thread(target=button_loop, daemon=True)
    t_btn.start()

def loop():
    global uncomfortable_flag

    # Light calibration (tune to your sensor)
    LIGHT_BRIGHT_RAW = 20
    LIGHT_DARK_RAW   = 140

    # Sound processing
    WINDOW_SAMPLES   = 40
    SPIKE_CAP        = 180
    BASELINE_ALPHA   = 0.05
    QUIET_LEARN_MAX  = 90
    SOUND_LEVEL_MAX  = 80

    baseline_pp = 0.0

    # thresholds for "uncomfortable"
    TEMP_COLD = 18.0
    TEMP_HOT  = 27.0
    LIGHT_TOO_DARK   = 15
    LIGHT_TOO_BRIGHT = 90
    SOUND_TOO_LOUD   = 70

    NEED_CONSEC = 4
    cold_n = hot_n = dark_n = bright_n = loud_n = 0

    while True:
        temp_c = read_temp_c()

        # Light %
        light_raw = read_stable(0, samples=8)
        light_pct = map_range_to_percent(
            LIGHT_DARK_RAW - light_raw,
            0,
            LIGHT_DARK_RAW - LIGHT_BRIGHT_RAW
        )

        # Sound %
        vals = [read_stable(1, samples=1) for _ in range(WINDOW_SAMPLES)]
        sound_pp = min(max(vals) - min(vals), SPIKE_CAP)

        if sound_pp <= QUIET_LEARN_MAX:
            baseline_pp = (1.0 - BASELINE_ALPHA) * baseline_pp + BASELINE_ALPHA * sound_pp

        sound_level = sound_pp - baseline_pp
        if sound_level < 0:
            sound_level = 0

        sound_pct = int(clamp(sound_level, 0, SOUND_LEVEL_MAX) * 100 / SOUND_LEVEL_MAX)

        # Detect reasons
        reasons = []

        # Temp
        if temp_c is None:
            cold_n = hot_n = 0
        else:
            if temp_c < TEMP_COLD:
                cold_n += 1; hot_n = 0
            elif temp_c > TEMP_HOT:
                hot_n += 1; cold_n = 0
            else:
                cold_n = hot_n = 0

        if cold_n >= NEED_CONSEC: reasons.append("FROID")
        if hot_n >= NEED_CONSEC: reasons.append("CHAUD")

        # Light
        dark_n = dark_n + 1 if light_pct < LIGHT_TOO_DARK else 0
        bright_n = bright_n + 1 if light_pct > LIGHT_TOO_BRIGHT else 0
        if dark_n >= NEED_CONSEC: reasons.append("SOMBRE")
        if bright_n >= NEED_CONSEC: reasons.append("LUMIERE")

        # Sound
        loud_n = loud_n + 1 if sound_pct > SOUND_TOO_LOUD else 0
        if loud_n >= NEED_CONSEC: reasons.append("BRUIT")

        uncomfortable_flag = (len(reasons) > 0)

        # Score random (placeholder)
        score = compute_study_score(temp_c, light_pct, sound_pct)

        # Console output
        temp_str = f"{temp_c:0.2f}C" if temp_c is not None else "N/A"
        base_line = f"Temp:{temp_str} | Light:{light_raw:3d} ({light_pct:3d}%) | Sound:{sound_pct:3d}% | Score:{score:3d}"
        if uncomfortable_flag:
            print(base_line + "  >>> INCONFORT: " + ", ".join(reasons))
        else:
            print(base_line)

        # LCD output (toggle with button)
        if show_score_mode:
            line0 = "Study Env Score"
            line1 = f"Score: {score:3d}/100"
        else:
            if uncomfortable_flag:
                line0 = "Incomfort:"
                reasons_str = ",".join(reasons)
                line1 = reasons_str[:16]
            else:
                line0 = f"T:{temp_str} L:{light_pct:3d}%"
                line1 = f"Sound:{sound_pct:3d}%"

        LCD1602.write(0, 0, pad16(line0))
        LCD1602.write(0, 1, pad16(line1))

        time.sleep(0.25)

def destroy():
    global stop_blinker, stop_button
    stop_blinker = True
    stop_button = True

    try:
        led_off()
        if p_R: p_R.stop()
        if p_G: p_G.stop()
        if p_B: p_B.stop()
    except:
        pass

    try:
        LCD1602.clear()
    except:
        pass

    GPIO.cleanup()

if __name__ == "__main__":
    try:
        setup()
        loop()
    except KeyboardInterrupt:
        pass
    finally:
        destroy()
