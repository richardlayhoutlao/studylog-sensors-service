from config import DS18B20_ID


def read_temp_c(sensor_id: str = DS18B20_ID):
    try:
        with open(f"/sys/bus/w1/devices/{sensor_id}/w1_slave", "r") as sensor_file:
            lines = sensor_file.read().splitlines()
        if not lines or "YES" not in lines[0]:
            return None
        return float(lines[1].split("t=")[1]) / 1000.0
    except Exception:
        return None
