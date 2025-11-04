import time, math, os
from breakout_bme280 import BreakoutBME280
from breakout_ltr559 import BreakoutLTR559
from machine import Pin
from pimoroni import Analog
import ujson
from enviro import i2c, activity_led, config, constants
import enviro.helpers as helpers
from phew import logging


# ================================================================
# 🔧 Constants
# ================================================================
RAIN_MM_PER_TICK = 0.2794
WIND_CM_RADIUS = 7.0
WIND_FACTOR = 0.0218
DAILY_STATS_FILE = "daily_stats.json"

bme280 = BreakoutBME280(i2c, constants.I2C_ADDR_BME280)
ltr559 = BreakoutLTR559(i2c)

wind_direction_pin = Analog(constants.WIND_DIRECTION_PIN)
wind_speed_pin = Pin(constants.WIND_SPEED_PIN, Pin.IN, Pin.PULL_UP)
rain_pin = Pin(constants.RAIN_PIN, Pin.IN, Pin.PULL_DOWN)
last_rain_trigger = False

def startup(reason):
  logging.info(f"> starting weather")
  global last_rain_trigger
  import wakeup

  # check if rain sensor triggered wake
  rain_sensor_trigger = wakeup.get_gpio_state() & (1 << 10)

  if rain_sensor_trigger:
    # read the current rain entries
    log_rain()

    last_rain_trigger = True

    # if we were woken by the RTC or a Poke continue with the startup
    return (reason is constants.WAKE_REASON_RTC_ALARM 
      or reason is constants.WAKE_REASON_BUTTON_PRESS)

  # there was no rain trigger so continue with the startup
  return True

def check_trigger():
  global last_rain_trigger
  rain_sensor_trigger = rain_pin.value()

  logging.info(f"> checking trigger ")

  if rain_sensor_trigger and not last_rain_trigger:
    activity_led(100)
    time.sleep(0.05)
    activity_led(0)

    log_rain()

  last_rain_trigger = rain_sensor_trigger

# ================================================================
# ☔ Rain Handling
# ================================================================

def log_rain():
  """Add one rain bucket tip, store timestamp, and update totals."""
  data = load_daily_stats()

  data["rain_ticks"] += 1
  data["rain_total_mm"] = round(data["rain_ticks"] * RAIN_MM_PER_TICK, 3)

  # append timestamp for per-hour computation
  ts = helpers.datetime_string()
  events = data.get("rain_events", [])
  events.append(ts)
  # keep at most ~190 events (fits < one FS block comfortably)
  if len(events) > 190:
      events = events[-190:]
  data["rain_events"] = events

  save_daily_stats(data)
  logging.info(f"> Rain tick recorded ({data['rain_total_mm']} mm total)")

# ================================================================
# 💨 Wind Handling
# ================================================================

def wind_speed(sample_time_ms=1000):
    """Measure current wind speed in m/s."""
    state = wind_speed_pin.value()
    ticks = []
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) <= sample_time_ms:
        now = wind_speed_pin.value()
        if now != state:
            ticks.append(time.ticks_ms())
            state = now

    if len(ticks) < 2:
        return 0.0

    avg_tick_ms = (time.ticks_diff(ticks[-1], ticks[0])) / (len(ticks) - 1)
    if avg_tick_ms == 0:
        return 0.0

    rotation_hz = (1000 / avg_tick_ms) / 2
    circumference = WIND_CM_RADIUS * 2.0 * math.pi
    return rotation_hz * circumference * WIND_FACTOR

def update_wind_stats(current_speed):
    """Update average and max gust in daily stats."""
    data = load_daily_stats()
    data["wind_samples"].append(current_speed)
    if len(data["wind_samples"]) > 50:
        data["wind_samples"] = data["wind_samples"][-50:]
    if current_speed > data.get("wind_gust", 0):
        data["wind_gust"] = round(current_speed, 2)
    save_daily_stats(data)
    avg_speed = sum(data["wind_samples"]) / len(data["wind_samples"])
    return round(avg_speed, 2), data["wind_gust"]

# ================================================================
# 🌬️ Wind Direction
# ================================================================

def wind_direction():
    ADC_TO_DEGREES = (
        2.533, 1.308, 1.487, 0.270, 0.300, 0.212, 0.595, 0.408,
        0.926, 0.789, 2.031, 1.932, 3.046, 2.667, 2.859, 2.265
    )

    value = wind_direction_pin.read_voltage()
    closest_index = min(range(16), key=lambda i: abs(ADC_TO_DEGREES[i] - value))
    wind_dir = closest_index * 22.5
    return (wind_dir + 360 + config.wind_direction_offset) % 360

# ================================================================
# 🌧️ Rain Summary and Pollen Index
# ================================================================

def rainfall(seconds_since_last):
  """
  Returns:
    amount (mm since last reading),
    per_second (mm/s over last interval),
    per_hour (mm in last 3600s),
    today (mm total today)
  """
  data = load_daily_stats()

  ticks_now = data.get("rain_ticks", 0)
  last_count = data.get("rain_last_count", ticks_now)

  # amount since last reading (in mm)
  delta_ticks = max(0, ticks_now - last_count)
  amount = round(delta_ticks * RAIN_MM_PER_TICK, 4)

  # mm/s since last reading
  per_second = 0.0
  if seconds_since_last and seconds_since_last > 0:
      per_second = round(amount / float(seconds_since_last), 6)

  # mm in last 3600s window, using timestamped events
  per_hour = 0.0
  events = data.get("rain_events", [])
  if events:
      now_ts = helpers.timestamp(helpers.datetime_string())
      one_hour_ago = now_ts - 3600
      tips_last_hour = 0
      for iso in events:
          try:
              t = helpers.timestamp(iso)
              if t >= one_hour_ago:
                  tips_last_hour += 1
          except Exception:
              pass
      per_hour = round(tips_last_hour * RAIN_MM_PER_TICK, 4)

  # total today in mm
  today = round(data.get("rain_total_mm", 0.0), 3)

  # update last_count so next read reports only the new delta
  data["rain_last_count"] = ticks_now
  save_daily_stats(data)

  return amount, per_second, per_hour, today

def estimate_pollen_index(temperature, humidity, wind_speed, rain_today, luminance):
    """
    Retorna um índice de 0 a 5 baseado em condições ambientais.
    Essa estimativa é qualitativa — não mede pólen diretamente.
    """
    score = 0

    # Temperatura: mais calor, mais liberação de pólen
    if temperature > 15: score += 1
    if temperature > 20: score += 1
    if temperature > 25: score += 1

    # Umidade: baixa umidade → pólen se dispersa mais
    if humidity < 70: score += 1
    if humidity < 50: score += 1

    # Vento: mais vento → transporte de pólen
    if wind_speed > 2: score += 1
    if wind_speed > 4: score += 1

    # Chuva: reduz concentração temporariamente
    if rain_today > 0: score -= 2

    # Luminosidade: dias ensolarados favorecem liberação
    if luminance > 10000: score += 1

    # Mantém dentro dos limites 0–5
    score = max(0, min(5, score))
    return int(score)

# ================================================================
# 📊 Unified Daily Statistics System
# ================================================================

def load_daily_stats():
    """Load or create daily statistics JSON file."""
    today = helpers.date_string()
    base = {
      "date": today,
      "rain_ticks": 0,
      "rain_total_mm": 0.0,
      "rain_events": [],          # NEW: timestamps (ISO strings) for per-hour calc
      "rain_last_count": 0,       # NEW: tick counter at last reading (to get delta)
      "wind_gust": 0.0,
      "wind_samples": [],
      "temperature": {"min": 999.0, "max": -999.0, "sum": 0.0, "count": 0},
      "humidity": {"min": 999.0, "max": -999.0, "sum": 0.0, "count": 0},
    }

    if helpers.file_exists(DAILY_STATS_FILE):
        try:
            with open(DAILY_STATS_FILE, "r") as f:
                data = ujson.load(f)
            if data.get("date") == today:
                base.update(data)
            else:
                logging.info("> New day detected — resetting daily stats.")
                save_daily_stats(base)
        except Exception as e:
            logging.error(f"! Failed to read {DAILY_STATS_FILE}: {e}")
            save_daily_stats(base)
    else:
        save_daily_stats(base)
    return base


def save_daily_stats(data):
    """Save stats to JSON file."""
    with open(DAILY_STATS_FILE, "w") as f:
        ujson.dump(data, f)

# ================================================================
# 🌡️ Temperature and Humidity Tracking
# ================================================================

def update_temp_humidity_stats(temp, hum):
    """Update daily min, max, and average for temperature and humidity."""
    data = load_daily_stats()

    for key, value in [("temperature", temp), ("humidity", hum)]:
        stats = data[key]
        stats["min"] = min(stats["min"], value)
        stats["max"] = max(stats["max"], value)
        stats["sum"] += value
        stats["count"] += 1
        data[key] = stats

    save_daily_stats(data)
    temp_avg = data["temperature"]["sum"] / data["temperature"]["count"]
    hum_avg = data["humidity"]["sum"] / data["humidity"]["count"]
    return round(temp_avg, 2), round(hum_avg, 2)

# ================================================================
# 📈 Main Sensor Readings
# ================================================================

def get_sensor_readings(seconds_since_last, is_usb_power):
  bme280.read()
  time.sleep(0.1)
  bme280_data = bme280.read()
  ltr_data = ltr559.get_reading()
  rain, rain_per_second, rain_per_hour, rain_today = rainfall(seconds_since_last)

  pressure = bme280_data[1] / 100.0
  temperature = bme280_data[0]
  humidity = bme280_data[2]

  avg_temp, avg_hum = update_temp_humidity_stats(temperature, humidity)

  current_wind = wind_speed()
  avg_wind, gust_wind = update_wind_stats(current_wind)
  wind_dir = wind_direction()
  daily_stats = load_daily_stats()

  from ucollections import OrderedDict
  readings = OrderedDict({
    "temperature": round(temperature, 2),
    "humidity": round(humidity, 2),
    "pressure": round(pressure, 2),
    "luminance": round(ltr_data[BreakoutLTR559.LUX], 2),

    "wind_speed": avg_wind,
    "wind_gust": gust_wind,
    "wind_direction": wind_dir,

    # ✅ Rain metrics restored
    "rain": round(rain, 4),
    "rain_per_second": round(rain_per_second, 6),
    "rain_per_hour": round(rain_per_hour, 4),
    "rain_today": round(rain_today, 3),

    "dewpoint": round(helpers.calculate_dewpoint(temperature, humidity), 2),

    "temperature_avg": avg_temp,
    "temperature_min": round(daily_stats["temperature"]["min"], 2),
    "temperature_max": round(daily_stats["temperature"]["max"], 2),
    "humidity_min": round(daily_stats["humidity"]["min"], 2),
    "humidity_max": round(daily_stats["humidity"]["max"], 2),

    "pollen_index": estimate_pollen_index(
        temperature, humidity, avg_wind, rain_today, ltr_data[BreakoutLTR559.LUX]
    ),
  })

  if config.sea_level_pressure:
      sea_level_pressure = round(
          helpers.get_sea_level_pressure(pressure, temperature, config.height_above_sea_level), 2
      )
      readings["sea_level_pressure"] = sea_level_pressure

  return readings
