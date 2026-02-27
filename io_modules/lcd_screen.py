from utils import pad16


class LCDScreen:
    def __init__(self, lcd_driver):
        self.lcd = lcd_driver

    def clear(self):
        self.lcd.clear()

    def show_score(self, score):
        line0 = "Study Env Score"
        line1 = f"Score: {score:3d}/100"
        self.lcd.write(0, 0, pad16(line0))
        self.lcd.write(0, 1, pad16(line1))

    def show_stats(self, temp_str, light_pct, sound_pct, is_uncomfortable, reasons):
        if is_uncomfortable:
            line0 = "Incomfort:"
            line1 = ",".join(reasons)[:16]
        else:
            line0 = f"T:{temp_str} L:{light_pct:3d}%"
            line1 = f"Sound:{sound_pct:3d}%"

        self.lcd.write(0, 0, pad16(line0))
        self.lcd.write(0, 1, pad16(line1))
