"""Sensor platform for Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ACTIVE_HEATING_ROOMS,
    ATTR_SYSTEM_HEATING_DEMAND,
    ATTR_TOTAL_ROOMS,
    DOMAIN,
    MANUFACTURER,
    MODEL_GATEWAY,
)
from .coordinator import ContromeDataUpdateCoordinator
from controme_scraper.models import Gateway

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Controme sensor entities from a config entry."""
    coordinator: ContromeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create system-level sensors
    entities = [
        ContromeSystemHeatingDemandSensor(coordinator),
        ContromeActiveHeatingRoomsSensor(coordinator),
    ]

    # Create valve position sensors for each thermostat
    thermostats = coordinator.data.get("thermostats", [])
    for thermostat in thermostats:
        if thermostat.valve_positions:
            # Create sensor for each valve assigned to this thermostat
            for idx, _ in enumerate(thermostat.valve_positions):
                entities.append(
                    ContromeValvePositionSensor(coordinator, thermostat.device_id, idx)
                )
    
    # Create return flow temperature sensors assigned to thermostats
    for thermostat in thermostats:
        if thermostat.return_flow_temperatures:
            for idx, temp in enumerate(thermostat.return_flow_temperatures):
                if temp is not None:
                    entities.append(
                        ContromeReturnFlowTemperatureSensor(
                            coordinator, 
                            thermostat.device_id, 
                            idx
                        )
                    )

    _LOGGER.info("Setting up %d Controme sensor entities", len(entities))
    async_add_entities(entities)


class ContromeSystemHeatingDemandSensor(CoordinatorEntity, SensorEntity):
    """Sensor for overall system heating demand (average valve position)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator: ContromeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"controme_system_heating_demand"
        self._attr_name = "System Heating Demand"

    @property
    def gateway(self) -> Gateway | None:
        """Get the gateway data from coordinator."""
        return self.coordinator.data.get("gateway")

    @property
    def native_value(self) -> float | None:
        """Return the system average valve position."""
        # Calculate from thermostats
        thermostats = self.coordinator.data.get("thermostats", [])
        all_positions = []
        for t in thermostats:
            if t.valve_positions:
                all_positions.extend(t.valve_positions)
        
        if all_positions:
            return int(sum(all_positions) / len(all_positions))
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        gateway = self.gateway
        if not gateway:
            return {}

        return {
            "identifiers": {(DOMAIN, gateway.gateway_id)},
            "name": gateway.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL_GATEWAY,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        thermostats = self.coordinator.data.get("thermostats", [])
        
        # Count active heating thermostats
        active_heating = sum(1 for t in thermostats if t.is_heating)
        
        return {
            "total_thermostats": len(thermostats),
            "active_heating_thermostats": active_heating,
        }

    @property
    def icon(self) -> str:
        """Return dynamic icon based on heating demand."""
        gateway = self.gateway
        if not gateway:
            return "mdi:gauge"

        avg = gateway.system_average_valve_position
        if avg is None:
            return "mdi:gauge"
        elif avg < 10:
            return "mdi:gauge-empty"
        elif avg < 30:
            return "mdi:gauge-low"
        elif avg < 70:
            return "mdi:gauge"
        else:
            return "mdi:gauge-full"


class ContromeActiveHeatingRoomsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for number of thermostats currently heating."""

    _attr_has_entity_name = True
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: ContromeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"controme_active_heating_thermostats"
        self._attr_name = "Active Heating Thermostats"

    @property
    def gateway(self) -> Gateway | None:
        """Get the gateway data from coordinator."""
        return self.coordinator.data.get("gateway")

    @property
    def native_value(self) -> int | None:
        """Return the number of thermostats actively heating."""
        thermostats = self.coordinator.data.get("thermostats", [])
        return sum(1 for t in thermostats if t.is_heating)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        gateway = self.gateway
        if not gateway:
            return {}

        return {
            "identifiers": {(DOMAIN, gateway.gateway_id)},
            "name": gateway.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL_GATEWAY,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        thermostats = self.coordinator.data.get("thermostats", [])
        
        return {
            "total_thermostats": len(thermostats),
        }


class ContromeValvePositionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual valve position assigned to a thermostat."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:valve"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
        valve_index: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._valve_index = valve_index
        self._attr_unique_id = f"controme_{device_id.replace('*', '_')}_valve_{valve_index}"
        
        # Set name based on thermostat
        thermostat = self._get_thermostat()
        valve_name = f"Valve {valve_index + 1}" if thermostat and len(thermostat.valve_positions or []) > 1 else "Valve"
        self._attr_name = valve_name

    def _get_thermostat(self):
        """Get the thermostat from coordinator data."""
        thermostats = self.coordinator.data.get("thermostats", [])
        return next((t for t in thermostats if t.device_id == self._device_id), None)

    @property
    def native_value(self) -> int | None:
        """Return the valve position."""
        thermostat = self._get_thermostat()
        if not thermostat or not thermostat.valve_positions:
            return None
        
        if self._valve_index < len(thermostat.valve_positions):
            return thermostat.valve_positions[self._valve_index]
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information - link to thermostat device."""
        from .const import MODEL_THERMOSTAT
        thermostat = self._get_thermostat()
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
        """Return additional state attributes."""
        thermostat = self._get_thermostat()
        if not thermostat:
            return {}

        attrs = {
            "device_id": self._device_id,
            "thermostat_name": thermostat.name,
        }
        
        # Add max position if available (hydraulic balancing limit)
        if thermostat.max_valve_positions and self._valve_index < len(thermostat.max_valve_positions):
            max_position = thermostat.max_valve_positions[self._valve_index]
            attrs["max_position"] = max_position
            
            # Calculate relative position (current / max * 100)
            if thermostat.valve_positions and self._valve_index < len(thermostat.valve_positions):
                current_position = thermostat.valve_positions[self._valve_index]
                if max_position > 0:
                    relative_position = round((current_position / max_position) * 100, 1)
                    attrs["relative_position"] = relative_position
        
        attrs["valve_index"] = self._valve_index
        attrs["total_valves"] = len(thermostat.valve_positions) if thermostat.valve_positions else 0
        
        # Add return flow temperature if available
        if thermostat.return_flow_temperatures and self._valve_index < len(thermostat.return_flow_temperatures):
            return_temp = thermostat.return_flow_temperatures[self._valve_index]
            if return_temp is not None:
                attrs["return_flow_temperature"] = return_temp
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        thermostat = self._get_thermostat()
        if not thermostat or not thermostat.valve_positions:
            return False
        return self._valve_index < len(thermostat.valve_positions)


class ContromeReturnFlowTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Sensor for return flow temperature monitoring assigned to a thermostat."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-water"

    def __init__(
        self,
        coordinator: ContromeDataUpdateCoordinator,
        device_id: str,
        temp_index: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._temp_index = temp_index
        self._attr_unique_id = f"controme_{device_id.replace('*', '_')}_return_flow_{temp_index}"
        
        # Set name based on number of valves
        thermostat = self._get_thermostat()
        if thermostat and thermostat.return_flow_temperatures and len(thermostat.return_flow_temperatures) > 1:
            self._attr_name = f"Return Flow {temp_index + 1}"
        else:
            self._attr_name = "Return Flow"

    def _get_thermostat(self):
        """Get the thermostat from coordinator data."""
        thermostats = self.coordinator.data.get("thermostats", [])
        return next((t for t in thermostats if t.device_id == self._device_id), None)

    @property
    def native_value(self) -> float | None:
        """Return the return flow temperature."""
        thermostat = self._get_thermostat()
        if not thermostat or not thermostat.return_flow_temperatures:
            return None
        
        if self._temp_index < len(thermostat.return_flow_temperatures):
            return thermostat.return_flow_temperatures[self._temp_index]
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information - link to thermostat device."""
        from .const import MODEL_THERMOSTAT
        thermostat = self._get_thermostat()
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
        """Return additional state attributes."""
        thermostat = self._get_thermostat()
        if not thermostat:
            return {}

        attrs = {
            "device_id": self._device_id,
            "thermostat_name": thermostat.name,
            "temp_index": self._temp_index,
        }
        
        # Add corresponding valve position if available
        if thermostat.valve_positions and self._temp_index < len(thermostat.valve_positions):
            attrs["valve_position"] = thermostat.valve_positions[self._temp_index]
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        thermostat = self._get_thermostat()
        if not thermostat or not thermostat.return_flow_temperatures:
            return False
        return self._temp_index < len(thermostat.return_flow_temperatures)
