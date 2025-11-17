"""Select platform for Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
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
    """Set up Controme select entities from a config entry."""
    coordinator: ContromeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create select entities for each thermostat
    entities = []
    thermostats: list[Thermostat] = coordinator.data.get("thermostats", [])
    
    for thermostat in thermostats:
        # 2 select entities per thermostat
        entities.append(ContromeDeviceType(coordinator, thermostat.device_id))
        entities.append(ContromeRoomAssignment(coordinator, thermostat.device_id))
    
    _LOGGER.info("Setting up %d Controme select entities", len(entities))
    async_add_entities(entities)


class ContromeSelectBase(CoordinatorEntity, SelectEntity):
    """Base class for Controme select entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
        key: str,
        name: str,
        options: list[str],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_unique_id = f"controme_{device_id.replace('*', '_')}_{key}"
        self._attr_name = name
        self._attr_options = options
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

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.info(
            "Setting %s for thermostat %s to %s",
            self._key,
            self._device_id,
            option,
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

        # Convert option to parameter value
        param_value = self._option_to_value(option)

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
                option,
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
        param_map = {
            "device_type": "deviceType",
            "room_assignment": "roomID",
        }
        return param_map.get(self._key)

    def _option_to_value(self, option: str) -> str:
        """Convert display option to API value."""
        # Override in subclass if needed
        return option

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


class ContromeDeviceType(ContromeSelectBase):
    """Select entity for thermostat device type.
    
    Note: Changes may take up to 60 seconds to appear on the physical device.
    """

    _attr_icon = "mdi:thermostat"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the device type entity."""
        options = [
            "undef",
            "hktGenius",
            "hkt",
            "hktControme",
            "hkteTRV",
        ]
        super().__init__(coordinator, device_id, "device_type", "Device Type", options)

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        thermostat = self.thermostat
        if not thermostat or not thermostat.device_type:
            return "undef"
        return thermostat.device_type


class ContromeRoomAssignment(ContromeSelectBase):
    """Select entity for room assignment.
    
    Note: Changes may take up to 60 seconds to appear on the physical device.
    """

    _attr_icon = "mdi:home-outline"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the room assignment entity."""
        # Get available rooms from coordinator data
        # This should be fetched from the actual Controme system
        # For now, using static list based on analysis
        options = [
            "Not Assigned",
            "Wohnzimmer",
            "Schlafzimmer",
            "Badezimmer",
            "Zimmer Paulina",
            "Zimmer Sophia",
            "Gästezimmer",
            "Büro",
        ]
        super().__init__(coordinator, device_id, "room_assignment", "Room Assignment", options)

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        thermostat = self.thermostat
        if not thermostat:
            return "Not Assigned"
        
        # Map room_id to room name
        if thermostat.room_name:
            return thermostat.room_name
        
        return "Not Assigned"
