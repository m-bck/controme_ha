"""Constants for the Controme Smart-Heat-OS integration."""
from datetime import timedelta

# Integration domain
DOMAIN = "controme"

# Platforms
PLATFORMS = ["climate", "sensor", "number", "select", "switch"]

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_HOUSE_ID = "house_id"

# Default values
DEFAULT_NAME = "Controme"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
DEFAULT_TIMEOUT = 30
DEFAULT_HOUSE_ID = 1

# Attributes
ATTR_VALVE_POSITIONS = "valve_positions"
ATTR_AVERAGE_VALVE_POSITION = "average_valve_position"
ATTR_FLOOR = "floor"
ATTR_ROOM_ID = "room_id"
ATTR_IS_HEATING = "is_heating"
ATTR_TARGET_OFFSET = "target_temperature_offset"
ATTR_SYSTEM_HEATING_DEMAND = "system_heating_demand"
ATTR_ACTIVE_HEATING_ROOMS = "active_heating_rooms"
ATTR_TOTAL_ROOMS = "total_rooms"

# Device info
MANUFACTURER = "Controme GmbH"
MODEL_GATEWAY = "Controme Gateway"
MODEL_ROOM = "Room Climate Control"
MODEL_THERMOSTAT = "Raumcontroller"
