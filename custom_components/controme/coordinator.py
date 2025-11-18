"""DataUpdateCoordinator for Controme Smart-Heat-OS integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from controme_scraper.controller import ContromeController
from controme_scraper.models import Gateway

_LOGGER = logging.getLogger(__name__)


class ContromeDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Controme data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        controller: ContromeController,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.controller = controller
        self.gateway_id = "main"
        self.gateway_name = "Controme Gateway"

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Controme."""
        try:
            # Fetch all thermostats (includes config, valve data, and return flow temps)
            from functools import partial
            thermostats = await self.hass.async_add_executor_job(
                partial(self.controller.get_thermostats, include_config=True, include_valve_data=True)
            )
            
            if thermostats is None:
                raise UpdateFailed("Failed to fetch thermostats from Controme")
            
            # Fetch sensors (for standalone return flow sensors)
            sensors = await self.hass.async_add_executor_job(
                self.controller.get_sensors
            )
            
            # Create Gateway object with system-wide metrics
            # Calculate from thermostats instead of rooms
            all_valve_positions = []
            for t in thermostats:
                all_valve_positions.extend(t.valve_positions)
            
            avg_valve_position = None
            if all_valve_positions:
                avg_valve_position = int(sum(all_valve_positions) / len(all_valve_positions))
            
            gateway = Gateway(
                gateway_id=self.gateway_id,
                name=self.gateway_name,
                ip_address=self.controller.host,
                firmware_version=None,  # Could be fetched from system info endpoint
                rooms=[],  # No longer used, thermostats are primary
            )
            
            _LOGGER.debug(
                "Successfully updated Controme data: %d thermostats, %d sensors, system demand: %s%%",
                len(thermostats),
                len(sensors) if sensors else 0,
                avg_valve_position,
            )
            
            return {
                "thermostats": thermostats,
                "gateway": gateway,
                "sensors": sensors or [],
            }
            
        except Exception as err:
            _LOGGER.error("Error updating Controme data: %s", err)
            raise UpdateFailed(f"Error communicating with Controme: {err}") from err
