from config import (
    BASELINE_ALPHA,
    QUIET_LEARN_MAX,
    SOUND_LEVEL_MAX,
    SPIKE_CAP,
    WINDOW_SAMPLES,
)
from utils import clamp, read_stable


class SoundLevelProcessor:
    def __init__(self):
        self.baseline_pp = 0.0

    def read_sound_percent(self, adc, channel: int = 1):
        values = [read_stable(adc, channel, samples=1) for _ in range(WINDOW_SAMPLES)]
        sound_pp = min(max(values) - min(values), SPIKE_CAP)

        if sound_pp <= QUIET_LEARN_MAX:
            self.baseline_pp = (
                (1.0 - BASELINE_ALPHA) * self.baseline_pp
                + BASELINE_ALPHA * sound_pp
            )

        sound_level = sound_pp - self.baseline_pp
        if sound_level < 0:
            sound_level = 0

        sound_pct = int(clamp(sound_level, 0, SOUND_LEVEL_MAX) * 100 / SOUND_LEVEL_MAX)
        return sound_pct
