"""Number platform for Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL_THERMOSTAT
from .coordinator import ContromeDataUpdateCoordinator
from controme_scraper.models import Thermostat

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Controme number entities from a config entry."""
    coordinator: ContromeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create number entities for each thermostat
    entities = []
    thermostats: list[Thermostat] = coordinator.data.get("thermostats", [])
    
    for thermostat in thermostats:
        # 6 number entities per thermostat
        entities.append(ContromeSensorOffset(coordinator, thermostat.device_id))
        entities.append(ContromeDisplayBrightness(coordinator, thermostat.device_id))
        entities.append(ContromeSendInterval(coordinator, thermostat.device_id))
        entities.append(ContromeDeviation(coordinator, thermostat.device_id))
        entities.append(ContromeForceSendCount(coordinator, thermostat.device_id))
    
    _LOGGER.info("Setting up %d Controme number entities", len(entities))
    async_add_entities(entities)


class ContromeNumberBase(CoordinatorEntity, NumberEntity):
    """Base class for Controme number entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
        key: str,
        name: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_unique_id = f"controme_{device_id.replace('*', '_')}_{key}"
        self._attr_name = name
        self._last_change_time = None

    @property
    def thermostat(self) -> Thermostat | None:
        """Get the current thermostat data from coordinator."""
        thermostats: list[Thermostat] = self.coordinator.data.get("thermostats", [])
        return next((t for t in thermostats if t.device_id == self._device_id), None)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this entity."""
        thermostat = self.thermostat
        if not thermostat:
            return {}
        
        return {
            "identifiers": {(DOMAIN, thermostat.device_id)},
            "name": thermostat.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL_THERMOSTAT,
            "sw_version": thermostat.firmware_version,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        # Validate brightness range (0-30 for Controme)
        if self._key == "display_brightness" and value > 30:
            _LOGGER.warning(
                "Display brightness max is 30, clamping value from %s to 30",
                value,
            )
            value = 30
        
        _LOGGER.info(
            "Setting %s for thermostat %s to %s",
            self._key,
            self._device_id,
            value,
        )

        # Extract device number from device_id (RFAktor*1 -> 1)
        try:
            device_num = int(self._device_id.split('*')[1])
        except (IndexError, ValueError) as err:
            _LOGGER.error(
                "Failed to extract device number from %s: %s",
                self._device_id,
                err,
            )
            return

        # Get the parameter name for this entity type
        param_name = self._get_parameter_name()
        if not param_name:
            _LOGGER.error("Unknown parameter name for key %s", self._key)
            return

        # Call the web_client method
        success = await self.hass.async_add_executor_job(
            self.coordinator.controller.web_client.set_thermostat_parameter,
            device_num,
            param_name,
            str(int(value)) if isinstance(value, float) else str(value),
        )

        if success:
            _LOGGER.info(
                "Successfully updated %s to %s (changes may take up to 60 seconds to appear on device)",
                self._key,
                value,
            )
            # Track last change time for cooldown
            from datetime import datetime
            self._last_change_time = datetime.now()
            
            # Request coordinator update after a short delay
            await self.coordinator.async_request_refresh()
            
            # Schedule re-enabling after 60 seconds
            self.async_write_ha_state()
        else:
            _LOGGER.error(
                "Failed to update %s for thermostat %s",
                self._key,
                self._device_id,
            )

    def _get_parameter_name(self) -> str | None:
        """Get the Controme API parameter name for this entity."""
        # Map entity keys to Controme API parameter names
        param_map = {
            "sensor_offset": "sensorOffset",
            "display_brightness": "dispBright",
            "send_interval": "sendInterval",
            "deviation": "deviation",
            "force_send_count": "forceSendCount",
        }
        return param_map.get(self._key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check coordinator availability first
        if not super().available:
            return False
        
        # During cooldown period (60 seconds after change), entity is not available
        if self._last_change_time:
            from datetime import datetime, timedelta
            elapsed = datetime.now() - self._last_change_time
            if elapsed < timedelta(seconds=60):
                return False
        
        return True


class ContromeSensorOffset(ContromeNumberBase):
    """Number entity for thermostat sensor offset (temperature calibration).
    
    Note: Changes may take up to 60 seconds to appear on the physical device.
    """

    _attr_native_min_value = -5.0
    _attr_native_max_value = 5.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "°C"
    _attr_icon = "mdi:thermometer-lines"
    _attr_entity_category = None  # User-facing setting

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor offset entity."""
        super().__init__(coordinator, device_id, "sensor_offset", "Sensor Offset")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        thermostat = self.thermostat
        return thermostat.sensor_offset if thermostat else None


class ContromeDisplayBrightness(ContromeNumberBase):
    """Number entity for thermostat display brightness.
    
    Note: Changes may take up to 60 seconds to appear on the physical device
    due to the RF communication interval.
    """

    _attr_native_min_value = 0
    _attr_native_max_value = 30
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:brightness-6"
    _attr_entity_category = None  # User-facing setting

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the display brightness entity."""
        super().__init__(coordinator, device_id, "display_brightness", "Display Brightness")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        thermostat = self.thermostat
        return float(thermostat.display_brightness) if thermostat else None


class ContromeSendInterval(ContromeNumberBase):
    """Number entity for thermostat send interval."""

    _attr_native_min_value = 60
    _attr_native_max_value = 3600
    _attr_native_step = 60
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the send interval entity."""
        super().__init__(coordinator, device_id, "send_interval", "Send Interval")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        thermostat = self.thermostat
        return float(thermostat.send_interval) if thermostat else None


class ContromeDeviation(ContromeNumberBase):
    """Number entity for temperature change threshold."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 0.5
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "°C"
    _attr_icon = "mdi:delta"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the deviation entity."""
        super().__init__(coordinator, device_id, "deviation", "Temperature Deviation")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        thermostat = self.thermostat
        return thermostat.deviation if thermostat else None


class ContromeForceSendCount(ContromeNumberBase):
    """Number entity for force send count."""

    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:counter"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the force send count entity."""
        super().__init__(coordinator, device_id, "force_send_count", "Force Send Count")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        thermostat = self.thermostat
        return float(thermostat.force_send_count) if thermostat else None
