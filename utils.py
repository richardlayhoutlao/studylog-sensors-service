def pad16(text: str) -> str:
    return (text + " " * 16)[:16]


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def read_stable(adc, channel: int, samples: int = 4, delay: float = 0.0008) -> int:
    import time

    total = 0
    for _ in range(samples):
        adc.read(channel)
        val = adc.read(channel)
        total += val
        time.sleep(delay)
    return total // samples


def map_range_to_percent(x, x_min, x_max):
    if x_max == x_min:
        return 0
    x = clamp(x, x_min, x_max)
    return int((x - x_min) * 100 / (x_max - x_min))


def compute_study_score(_temp_c, _light_pct, _sound_pct):
    temp_score = 100 - int(abs(_temp_c - 22) * 8)
    temp_score = clamp(temp_score, 0, 100)

    light_score = clamp(int(_light_pct), 0, 100)
    sound_score = 100 - clamp(int(_sound_pct), 0, 100)

    score = int(0.33 * temp_score + 0.33 * light_score + 0.33 * sound_score)
    return clamp(score, 0, 100)
