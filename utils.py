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
