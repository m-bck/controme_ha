"""Switch platform for Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up Controme switch entities from a config entry."""
    coordinator: ContromeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create switch entities for each thermostat
    entities = []
    thermostats: list[Thermostat] = coordinator.data.get("thermostats", [])
    
    for thermostat in thermostats:
        # 4 switch entities per thermostat
        entities.append(ContromeLock(coordinator, thermostat.device_id))
        entities.append(ContromeMainSensor(coordinator, thermostat.device_id))
        entities.append(ContromeTempModeTemporary(coordinator, thermostat.device_id))
        entities.append(ContromeBatterySavingMode(coordinator, thermostat.device_id))
    
    _LOGGER.info("Setting up %d Controme switch entities", len(entities))
    async_add_entities(entities)


class ContromeSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base class for Controme switch entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
        key: str,
        name: str,
        icon_on: str,
        icon_off: str,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_unique_id = f"controme_{device_id.replace('*', '_')}_{key}"
        self._attr_name = name
        self._icon_on = icon_on
        self._icon_off = icon_off
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

    @property
    def icon(self) -> str:
        """Return the icon based on state."""
        return self._icon_on if self.is_on else self._icon_off

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        _LOGGER.info(
            "Turning ON %s for thermostat %s",
            self._key,
            self._device_id,
        )
        await self._async_set_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        _LOGGER.info(
            "Turning OFF %s for thermostat %s",
            self._key,
            self._device_id,
        )
        await self._async_set_value(False)

    async def _async_set_value(self, value: bool) -> None:
        """Set the switch value."""
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

        # Convert boolean to string ("checked" for True, "" for False)
        param_value = "checked" if value else ""

        # Call the web_client method
        success = await self.hass.async_add_executor_job(
            self.coordinator.controller.web_client.set_thermostat_parameter,
            device_num,
            param_name,
            param_value,
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
            "locked": "locked",
            "is_main_sensor": "isMainSensor",
            "temp_mode_temporary": "tempModeTemporary",
            "battery_saving_mode": "batterySavingMode",
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


class ContromeLock(ContromeSwitchBase):
    """Switch entity for thermostat lock (prevents changes at device).
    
    Note: Changes may take up to 60 seconds to appear on the physical device.
    """

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the lock switch."""
        super().__init__(
            coordinator,
            device_id,
            "locked",
            "Lock",
            "mdi:lock",
            "mdi:lock-open",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        thermostat = self.thermostat
        return thermostat.locked if thermostat else False


class ContromeMainSensor(ContromeSwitchBase):
    """Switch entity for main sensor (determines room target temperature).
    
    Note: Changes may take up to 60 seconds to appear on the physical device.
    """

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the main sensor switch."""
        super().__init__(
            coordinator,
            device_id,
            "is_main_sensor",
            "Main Sensor",
            "mdi:thermometer-check",
            "mdi:thermometer",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        thermostat = self.thermostat
        return thermostat.is_main_sensor if thermostat else False


class ContromeTempModeTemporary(ContromeSwitchBase):
    """Switch entity for temporary temperature mode."""

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the temp mode temporary switch."""
        super().__init__(
            coordinator,
            device_id,
            "temp_mode_temporary",
            "Temporary Mode",
            "mdi:timer",
            "mdi:timer-off",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        thermostat = self.thermostat
        return thermostat.temp_mode_temporary if thermostat else False


class ContromeBatterySavingMode(ContromeSwitchBase):
    """Switch entity for battery saving mode."""

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the battery saving mode switch."""
        super().__init__(
            coordinator,
            device_id,
            "battery_saving_mode",
            "Battery Saving",
            "mdi:battery-heart-variant",
            "mdi:battery",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        thermostat = self.thermostat
        return thermostat.battery_saving_mode if thermostat else False
