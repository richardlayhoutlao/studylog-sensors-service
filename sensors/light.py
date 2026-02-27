from config import LIGHT_BRIGHT_RAW, LIGHT_DARK_RAW
from utils import map_range_to_percent, read_stable


def read_light(adc, channel: int = 0):
    light_raw = read_stable(adc, channel, samples=8)
    light_pct = map_range_to_percent(
        LIGHT_DARK_RAW - light_raw,
        0,
        LIGHT_DARK_RAW - LIGHT_BRIGHT_RAW,
    )
    return light_raw, light_pct
