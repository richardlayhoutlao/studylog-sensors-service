import threading
import time

import RPi.GPIO as GPIO

from config import BLINK_OFF, BLINK_ON, LED_B_PIN, LED_COMMON_ANODE, LED_G_PIN, LED_PWM_FREQ, LED_R_PIN
from utils import clamp


class RGBLedBlinker:
    def __init__(self):
        self.uncomfortable = False
        self._stop = False
        self._thread = None
        self._led_lock = threading.Lock()

        for pin in (LED_R_PIN, LED_G_PIN, LED_B_PIN):
            GPIO.setup(pin, GPIO.OUT)

        self._p_r = GPIO.PWM(LED_R_PIN, LED_PWM_FREQ)
        self._p_g = GPIO.PWM(LED_G_PIN, LED_PWM_FREQ)
        self._p_b = GPIO.PWM(LED_B_PIN, LED_PWM_FREQ)

        self._p_r.start(0)
        self._p_g.start(0)
        self._p_b.start(0)
        self.off()

    def _apply_pwm(self, pwm, val_0_100):
        val_0_100 = clamp(val_0_100, 0, 100)
        if LED_COMMON_ANODE:
            pwm.ChangeDutyCycle(100 - val_0_100)
        else:
            pwm.ChangeDutyCycle(val_0_100)

    def set_rgb(self, red, green, blue):
        with self._led_lock:
            self._apply_pwm(self._p_r, red)
            self._apply_pwm(self._p_g, green)
            self._apply_pwm(self._p_b, blue)

    def off(self):
        self.set_rgb(0, 0, 0)

    def _loop(self):
        is_on = False
        while not self._stop:
            if self.uncomfortable:
                is_on = not is_on
                if is_on:
                    self.set_rgb(100, 0, 0)
                    time.sleep(BLINK_ON)
                else:
                    self.off()
                    time.sleep(BLINK_OFF)
            else:
                self.set_rgb(0, 100, 0)
                time.sleep(0.05)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self.off()
        self._p_r.stop()
        self._p_g.stop()
        self._p_b.stop()
