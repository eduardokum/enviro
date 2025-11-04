# enviro config file

# you may edit this file by hand but if you enter provisioning mode
# then the file will be automatically overwritten with new details

provisioned = False

# enter a nickname for this board
nickname = None

# network access details
wifi_ssid = None
wifi_password = None
wifi_country = "GB"

# Adjust daily rain day for UK BST
uk_bst = True

# For local time corrections to daily rain logging other than BST
# Ignored if uk_bst = True
utc_offset = 0

# how often to wake up and take a reading (in minutes)
reading_frequency = 15

# how often to trigger a resync of the onboard RTC (in hours)
resync_frequency = 168

# Watchdog timer in whole minutes (integer), 0 is not active 
pio_watchdog_time = 10

# where to upload to ("http", "mqtt", "adafruit_io", "influxdb", "wunderground")
destination = None
# Optional secondary destination - this will consume more battery
# Cached uploads cleanup occurs only on primary destination success, this means
# secondary data will not retry if primary is successful, also secondary data
# will be reuploaded if the primary fails, ensure the secondary destination can
# handle duplicate uploads
# set to None if not in use
secondary_destination = None

# how often to upload data (number of cached readings)
upload_frequency = 5

# web hook settings
custom_http_url = None
custom_http_username = None
custom_http_password = None

# mqtt broker settings
mqtt_broker_address = None
mqtt_broker_username = None
mqtt_broker_password = None
# mqtt broker if using local SSL
mqtt_broker_ca_file = None

# Home Assistant Discovery setting
hass_discovery = False # This could arguably be set to a text field for better customisability 
hass_discovery_triggered = False

# adafruit ui settings
adafruit_io_username = None
adafruit_io_key = None

# influxdb settings
influxdb_org = None
influxdb_url = None
influxdb_token = None
influxdb_bucket = None

# weather underground settings
wunderground_id = None
wunderground_key = None

# grow specific settings
auto_water = False
moisture_target_a = 50
moisture_target_b = 50
moisture_target_c = 50

# weather specific settings
wind_direction_offset = 0

# compensate for usb power
usb_power_temperature_offset = 4.5

# sea level pressure conversion (adjusts measured pressure output for mean sea level value)
sea_level_pressure = False
# height in metres
height_above_sea_level = 0

# Feature toggles
enable_battery_voltage = False

# voltage calibration
voltage_calibration_factor = 1.000