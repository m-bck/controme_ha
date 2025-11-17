"""Climate platform for Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AVERAGE_VALVE_POSITION,
    ATTR_FLOOR,
    ATTR_IS_HEATING,
    ATTR_ROOM_ID,
    ATTR_VALVE_POSITIONS,
    DOMAIN,
    MANUFACTURER,
    MODEL_THERMOSTAT,
)
from .coordinator import ContromeDataUpdateCoordinator
from controme_scraper.models import Thermostat

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Controme climate entities from a config entry."""
    coordinator: ContromeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create climate entities for each thermostat
    entities = []
    thermostats: list[Thermostat] = coordinator.data.get("thermostats", [])
    
    for thermostat in thermostats:
        entities.append(ContromeClimate(coordinator, thermostat.device_id))
    
    _LOGGER.info("Setting up %d Controme climate entities (thermostats)", len(entities))
    async_add_entities(entities)


class ContromeClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Controme Thermostat as a Climate entity."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 5.0
    _attr_max_temp = 30.0

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"controme_thermostat_{device_id.replace('*', '_')}"

    @property
    def thermostat(self) -> Thermostat | None:
        """Get the current thermostat data from coordinator."""
        thermostats: list[Thermostat] = self.coordinator.data.get("thermostats", [])
        return next((t for t in thermostats if t.device_id == self._device_id), None)

    @property
    def name(self) -> str:
        """Return the name of the climate entity."""
        thermostat = self.thermostat
        return thermostat.name if thermostat else f"Thermostat {self._device_id}"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        thermostat = self.thermostat
        return thermostat.current_temperature if thermostat else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        thermostat = self.thermostat
        return thermostat.target_temperature if thermostat else None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        # Always return HEAT for floor heating (no cooling)
        return HVACMode.HEAT
    
    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action (heating/idle)."""
        thermostat = self.thermostat
        if thermostat and thermostat.is_heating:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def icon(self) -> str:
        """Return the icon for the entity."""
        # Icon now reflects hvac_action
        if self.hvac_action == HVACAction.HEATING:
            return "mdi:fire"
        return "mdi:home-thermometer"

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
            "suggested_area": thermostat.room_name or thermostat.floor_name,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes with all 12 configuration options."""
        thermostat = self.thermostat
        if not thermostat:
            return {}

        attrs = {
            # Device identity
            "device_id": thermostat.device_id,
            "mac_address": thermostat.mac_address,
            
            # Room assignment
            ATTR_ROOM_ID: thermostat.assigned_room_id,
            "room_name": thermostat.room_name,
            ATTR_FLOOR: thermostat.floor_name,
            
            # Configuration options (12 total)
            "device_type": thermostat.device_type,
            "sensor_offset": thermostat.sensor_offset,
            "display_brightness": thermostat.display_brightness,
            "send_interval": thermostat.send_interval,
            "deviation": thermostat.deviation,
            "force_send_count": thermostat.force_send_count,
            "locked": thermostat.locked,
            "is_main_sensor": thermostat.is_main_sensor,
            "temp_mode_temporary": thermostat.temp_mode_temporary,
            "battery_saving_mode": thermostat.battery_saving_mode,
            
            # Valve data
            ATTR_VALVE_POSITIONS: thermostat.valve_positions,
            ATTR_AVERAGE_VALVE_POSITION: thermostat.average_valve_position,
            "valve_count": len(thermostat.valve_positions),
            ATTR_IS_HEATING: thermostat.is_heating,
        }
        
        # Add relative valve positions if available
        if thermostat.max_valve_positions:
            attrs["max_valve_positions"] = thermostat.max_valve_positions
            attrs["relative_valve_positions"] = [
                round(p, 1) for p in thermostat.relative_valve_positions
            ]
            if thermostat.average_relative_valve_position is not None:
                attrs["average_relative_valve_position"] = round(
                    thermostat.average_relative_valve_position, 1
                )
        
        # Add return flow temperatures if available
        if thermostat.return_flow_temperatures:
            attrs["return_flow_temperatures"] = thermostat.return_flow_temperatures
        
        # Add status info
        if thermostat.battery_level is not None:
            attrs["battery_level"] = thermostat.battery_level
        if thermostat.signal_strength:
            attrs["signal_strength"] = thermostat.signal_strength
        
        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        _LOGGER.info(
            "Setting temperature for thermostat %s to %s°C",
            self._device_id,
            temperature,
        )

        # Get room_id from thermostat's assigned room
        thermostat = self.coordinator.data.get("thermostats", [])
        thermostat_data = next(
            (t for t in thermostat if t.device_id == self._device_id),
            None
        )
        
        if not thermostat_data or not thermostat_data.assigned_room:
            _LOGGER.error(
                "Cannot set temperature: thermostat %s not assigned to a room",
                self._device_id
            )
            return
        
        room_id = thermostat_data.assigned_room
        
        # Set room temperature via API
        success = await self.hass.async_add_executor_job(
            self.coordinator.controller.web_client.set_room_temperature,
            room_id,
            temperature,
        )
        
        if success:
            _LOGGER.info(
                "Successfully set room %s temperature to %s°C",
                room_id,
                temperature,
            )
            # Request immediate coordinator update
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set room %s temperature to %s°C",
                room_id,
                temperature,
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        _LOGGER.info(
            "Setting HVAC mode for thermostat %s to %s",
            self._device_id,
            hvac_mode,
        )

        # TODO: Implement HVAC mode setting
        # This might involve setting preset modes or enabling/disabling heating
        _LOGGER.warning(
            "HVAC mode setting not yet implemented - API endpoint needed"
        )
