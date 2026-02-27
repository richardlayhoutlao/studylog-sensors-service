import threading
import time

import RPi.GPIO as GPIO

from config import BTN_PIN, BUZZER_ACTIVE_LOW, BUZZER_PIN


class ButtonModeToggle:
    def __init__(self):
        self.show_score_mode = False
        self._stop = False
        self._thread = None

        GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)
        self.buzzer_off()

    def buzzer_on(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW if BUZZER_ACTIVE_LOW else GPIO.HIGH)

    def buzzer_off(self):
        GPIO.output(BUZZER_PIN, GPIO.HIGH if BUZZER_ACTIVE_LOW else GPIO.LOW)

    def buzzer_beep(self, duration=0.08):
        self.buzzer_on()
        time.sleep(duration)
        self.buzzer_off()

    def _loop(self):
        last = GPIO.input(BTN_PIN)

        while not self._stop:
            current = GPIO.input(BTN_PIN)

            if current == 0 and last == 1:
                self.buzzer_beep(0.08)
                self.show_score_mode = not self.show_score_mode
                print("Pressed -> mode:", "SCORE" if self.show_score_mode else "STATS")
                time.sleep(0.2)

            last = current
            time.sleep(0.03)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        self.buzzer_off()
