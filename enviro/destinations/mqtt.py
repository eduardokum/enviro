from enviro import logging
from enviro.constants import UPLOAD_SUCCESS, UPLOAD_FAILED, I2C_ADDR_LTR390
from enviro.mqttsimple import MQTTClient
from enviro import i2c_devices
import ujson
import config


def log_destination():
    logging.info(
        f"> uploading cached readings to MQTT broker: {config.mqtt_broker_address}"
    )


def upload_reading(reading):
    server = config.mqtt_broker_address
    username = config.mqtt_broker_username
    password = config.mqtt_broker_password
    nickname = reading["nickname"]

    try:
        if config.mqtt_broker_ca_file:
            # Using SSL
            f = open("ca.crt")
            ssl_data = f.read()
            f.close()
            mqtt_client = MQTTClient(
                reading["uid"],
                server,
                user=username,
                password=password,
                keepalive=60,
                ssl=True,
                ssl_params={"cert": ssl_data},
            )
        else:
            # Not using SSL
            mqtt_client = MQTTClient(
                reading["uid"], server, user=username, password=password, keepalive=60
            )
        # Now continue with connection and upload
        mqtt_client.connect()
        mqtt_client.publish(f"enviro/{nickname}", ujson.dumps(reading), retain=True)
        mqtt_client.disconnect()
        return UPLOAD_SUCCESS

    # Try disconneting to see if it prevents hangs on this typew of errors recevied so far
    except (OSError, IndexError) as exc:
        try:
            import sys, io

            buf = io.StringIO()
            sys.print_exception(exc, buf)
            logging.debug(f"  - an exception occurred when uploading.", buf.getvalue())
            mqtt_client.disconnect()
        except Exception as exc:
            import sys, io

            buf = io.StringIO()
            sys.print_exception(exc, buf)
            logging.debug(
                f"  - an exception occurred when disconnecting mqtt client.",
                buf.getvalue(),
            )

    except Exception as exc:
        import sys, io

        buf = io.StringIO()
        sys.print_exception(exc, buf)
        logging.debug(f"  - an exception occurred when uploading.", buf.getvalue())

    return UPLOAD_FAILED


def hass_discovery(board_type):
    logging.debug(f"> HASS Discovery initialized")
    try:
        server = config.mqtt_broker_address
        username = config.mqtt_broker_username
        password = config.mqtt_broker_password
        nickname = config.nickname
        # attempt to publish reading
        mqtt_client = MQTTClient(
            nickname, server, user=username, password=password, keepalive=60
        )
        mqtt_client.connect()
        logging.info(f"  - connected to mqtt broker")
    except:
        logging.error(f"  - an exception try to connect to mqtt to send HASS Discovery")

    mqtt_discovery(
        "Temperature",
        "temperature",
        "°C",
        "temperature",
        board_type,
        mqtt_client,
        "mdi:thermometer",
    )  # Temperature
    mqtt_discovery(
        "Pressure", "pressure", "hPa", "pressure", board_type, mqtt_client, "mdi:gauge"
    )  # Pressure
    mqtt_discovery(
        "Humidity",
        "humidity",
        "%",
        "humidity",
        board_type,
        mqtt_client,
        "mdi:water-percent",
    )  # Humidity
    mqtt_discovery(
        "Battery Voltage",
        "voltage",
        "V",
        "battery_voltage",
        board_type,
        mqtt_client,
        "mdi:car-battery",
    )  # Voltage
    mqtt_discovery(
        "Battery Percent", "battery", "%", "battery_percent", board_type, mqtt_client
    )  # Percent
    if board_type == "weather":
        mqtt_discovery(
            "Luminance",
            "illuminance",
            "lx",
            "luminance",
            board_type,
            mqtt_client,
            "mdi:brightness-5",
        )  # Luminance
        mqtt_discovery(
            "Wind Speed",
            "wind_speed",
            "m/s",
            "wind_speed",
            board_type,
            mqtt_client,
            "mdi:weather-windy",
        )  # Wind Speed
        mqtt_discovery(
            "Wind Gust",
            "wind_speed",
            "m/s",
            "wind_gust",
            board_type,
            mqtt_client,
            "mdi:weather-windy-variant",
        )  # Wind Gust
        mqtt_discovery(
            "Wind Direction",
            "none",
            "deg",
            "wind_direction",
            board_type,
            mqtt_client,
            "mdi:compass",
        )  # Wind Direction
        mqtt_discovery(
            "Rain",
            "precipitation",
            "mm",
            "rain",
            board_type,
            mqtt_client,
            "mdi:weather-rainy",
        )  # Rain
        mqtt_discovery(
            "Rain Per Second",
            "precipitation",
            "mm/s",
            "rain_per_second",
            board_type,
            mqtt_client,
            "mdi:weather-pouring",
        )  # Rain Per Second
        mqtt_discovery(
            "Rain Per Hour",
            "precipitation",
            "mm/h",
            "rain_per_hour",
            board_type,
            mqtt_client,
            "mdi:weather-pouring",
        )  # Rain Per Hour
        mqtt_discovery(
            "Rain Today",
            "precipitation",
            "mm",
            "rain_today",
            board_type,
            mqtt_client,
            "mdi:weather-rainy",
        )  # Rain Today
        mqtt_discovery(
            "Dew Point",
            "temperature",
            "°C",
            "dewpoint",
            board_type,
            mqtt_client,
            "mdi:water",
        )  # Dew point
        mqtt_discovery(
            "Temperature Min",
            "temperature",
            "°C",
            "temperature_min",
            board_type,
            mqtt_client,
            "mdi:thermometer-low",
        )  # Min Temperature
        mqtt_discovery(
            "Temperature Max",
            "temperature",
            "°C",
            "temperature_max",
            board_type,
            mqtt_client,
            "mdi:thermometer-high",
        )  # Max Temperature
        mqtt_discovery(
            "Humidity Min",
            "humidity",
            "%",
            "humidity_min",
            board_type,
            mqtt_client,
            "mdi:water-percent",
        )  # Min Humidity
        mqtt_discovery(
            "Humidity Max",
            "humidity",
            "%",
            "humidity_max",
            board_type,
            mqtt_client,
            "mdi:water-percent",
        )  # Max Humidity
        mqtt_discovery(
            "Pollen Index",
            "aqi",
            "Index",
            "pollen_index",
            board_type,
            mqtt_client,
            "mdi:flower-pollen",
        )  # Pollen Index
    elif board_type == "grow":
        mqtt_discovery(
            "Luminance", "illuminance", "lx", "luminance", board_type, mqtt_client
        )  # Luminance
        mqtt_discovery(
            "Moisture A", "humidity", "%", "moisture_a", board_type, mqtt_client
        )  # Moisture A
        mqtt_discovery(
            "Moisture B", "humidity", "%", "moisture_b", board_type, mqtt_client
        )  # Moisture B
        mqtt_discovery(
            "Moisture C", "humidity", "%", "moisture_c", board_type, mqtt_client
        )  # Moisture C
    elif board_type == "indoor":
        mqtt_discovery(
            "Luminance", "illuminance", "lx", "luminance", board_type, mqtt_client
        )  # Luminance
        # mqtt_discovery("Gas Resistance", "", "Ω", "gas_resistance", board_type, mqtt_client) # Gas Resistance //HASS doesn't support resistance as a device class//
        mqtt_discovery("AQI", "aqi", "&", "aqi", board_type, mqtt_client)  # AQI
        mqtt_discovery(
            "Colour Temperature",
            "temperature",
            "K",
            "color_temperature",
            board_type,
            mqtt_client,
        )  # Colo(u)r Temperature
    elif board_type == "urban":
        mqtt_discovery(
            "Noise", "voltage", "V", "noise", board_type, mqtt_client
        )  # Noise
        mqtt_discovery("PM1", "pm1", "µg/m³", "pm1", board_type, mqtt_client)  # PM1
        mqtt_discovery(
            "PM2.5", "pm25", "µg/m³", "pm2_5", board_type, mqtt_client
        )  # PM2_5
        mqtt_discovery("PM10", "pm10", "µg/m³", "pm10", board_type, mqtt_client)  # PM10

    if I2C_ADDR_LTR390 in i2c_devices:
        logging.info(f"  - HASS Discovered sensor LTR390")
        mqtt_discovery(
            "UV",
            "uv_index",
            "UV Index",
            "uv_index",
            board_type,
            mqtt_client,
            "mdi:weather-sunny-alert",
        )  # UV Index

    logging.info(f"  - HASS Discovery package sent")
    mqtt_client.disconnect()
    logging.info(f"  - disconnected from mqtt broker")


def mqtt_discovery(name, device_class, unit, value_name, model, mqtt_client, icon=None):
    nickname = config.nickname
    from ucollections import OrderedDict

    obj = OrderedDict(
        {
            "device": {
                "identifiers": [nickname],
                "name": nickname,
                "model": "Enviro " + model,
                "manufacturer": "Pimoroni",
            },
            "unit_of_measurement": unit,
            "device_class": device_class,
            "value_template": "{{ value_json.readings." + value_name + " }}",
            "state_class": "measurement",
            "state_topic": "enviro/" + nickname,
            "name": name,
            "unique_id": "sensor." + nickname + "." + value_name,
        }
    )
    if icon:
        obj["icon"] = icon  # HA aceita chave abreviada "ic" ou "icon"

    try:
        mqtt_client.publish(
            f"homeassistant/sensor/{nickname}/{value_name}/config",
            ujson.dumps(obj).encode("utf-8"),
            retain=True,
        )
        return UPLOAD_SUCCESS
    except:
        logging.error(
            f"  - an exception occurred when sending HASS Discovery homeassistant/sensor/{nickname}/{value_name}/config"
        )
