import adafruit_ltr390
from ucollections import OrderedDict
from phew import logging

def get_readings(i2c, address):
    uv_sensor = adafruit_ltr390.LTR390(i2c)
    uv_sensor.enable = True
    uv_sensor.mode = adafruit_ltr390.LTR390_MODE_UVS
    uv_sensor.gain = adafruit_ltr390.LTR390_GAIN_3
    uv_sensor.resolution = adafruit_ltr390.LTR390_RESOLUTION_18BIT

    readings = OrderedDict({
        "uv": uv_sensor.uvs,
        "uv_index": uv_sensor.uvs / 2300.0, 
    })

    for reading in readings:
        name_and_value = reading + " : " + str(readings[reading])
        logging.info(f"  - {name_and_value}")    

    return readings
