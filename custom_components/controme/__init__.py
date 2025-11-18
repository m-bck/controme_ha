"""The Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOUSE_ID, DEFAULT_HOUSE_ID, DOMAIN, PLATFORMS
from .coordinator import ContromeDataUpdateCoordinator
from controme_scraper.controller import ContromeController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Controme Smart-Heat-OS from a config entry."""
    # Create the Controme controller in executor to avoid blocking event loop
    try:
        controller = await hass.async_add_executor_job(
            ContromeController,
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data.get(CONF_HOUSE_ID, DEFAULT_HOUSE_ID),
        )
    except Exception as err:
        _LOGGER.error("Failed to create Controme controller: %s", err)
        raise ConfigEntryNotReady from err

    # Create the data update coordinator
    coordinator = ContromeDataUpdateCoordinator(hass, controller)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Migrate old room-based entities to thermostat-based entities
    await _async_migrate_entities(hass, entry)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_migrate_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate old room-based entities to new thermostat-based entities."""
    from homeassistant.helpers import entity_registry as er
    
    entity_reg = er.async_get(hass)
    
    # Remove old room-based climate entities (Room Climate Control)
    entities_to_remove = []
    for entity in er.async_entries_for_config_entry(entity_reg, entry.entry_id):
        # Identify old room entities by their unique_id pattern
        if entity.unique_id.startswith("controme_room_"):
            _LOGGER.info("Removing old room-based entity: %s", entity.entity_id)
            entities_to_remove.append(entity.entity_id)
    
    # Remove the old entities
    for entity_id in entities_to_remove:
        entity_reg.async_remove(entity_id)
    
    if entities_to_remove:
        _LOGGER.info("Migrated %d old room-based entities to thermostat-based entities", len(entities_to_remove))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove coordinator from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
