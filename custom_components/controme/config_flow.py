"""Config flow for Controme Smart-Heat-OS integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_HOUSE_ID, DEFAULT_HOUSE_ID, DOMAIN
from controme_scraper.heizung import ContromeController

_LOGGER = logging.getLogger(__name__)

# Schema for user input
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_HOUSE_ID, default=DEFAULT_HOUSE_ID): vol.Coerce(int),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Normalize host URL - add http:// if missing
    host = data[CONF_HOST].strip()
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    
    # Remove trailing slash
    if host.endswith("/"):
        host = host[:-1]
    
    # Create controller and try to fetch data to verify connection
    house_id = data.get(CONF_HOUSE_ID, DEFAULT_HOUSE_ID)
    
    # Create controller in executor to avoid blocking event loop
    def create_and_validate():
        controller = ContromeController(
            host=host,
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            house_id=house_id,
        )
        # Validate by fetching rooms
        controller.get_rooms()
        return controller
    
    # Try to create controller and fetch data to validate connection
    try:
        controller = await hass.async_add_executor_job(create_and_validate)
    except Exception as err:
        _LOGGER.error("Failed to connect to Controme: %s", err)
        raise CannotConnect from err
    
    # Return validated data
    return {
        "title": f"Controme ({host})",
        "host": host,
        "house_id": house_id,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Controme Smart-Heat-OS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create unique ID based on host and house_id
                unique_id = f"{info['host']}_{info['house_id']}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_HOST: info["host"],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_HOUSE_ID: info["house_id"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
