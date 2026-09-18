"""Config flow for the Scalable Capital integration."""

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    BRIDGE_HOSTS,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


class ScalableCapitalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Scalable Capital.

    No user input: the add-on is discovered automatically on the internal
    network by probing the known hostnames.
    """

    VERSION = 1

    async def _probe(self, url: str) -> bool:
        """Return True if the bridge answers /health."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{url}/health",
                timeout=aiohttp.ClientTimeout(total=2),
            ) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001
            return False

    async def _detect_bridge(self) -> str | None:
        """Return the first reachable bridge URL, or None."""
        for host in BRIDGE_HOSTS:
            url = f"http://{host}:{DEFAULT_PORT}"
            if await self._probe(url):
                return url
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step.

        The bridge is auto-detected on the internal network. If detection
        fails (e.g. the add-on runs under a different hostname), the user can
        enter the bridge URL manually.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            manual = (user_input.get(CONF_URL) or "").strip().rstrip("/")
            url = manual or await self._detect_bridge()
            if manual and not await self._probe(manual):
                errors[CONF_URL] = "cannot_connect"
            elif not url:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Scalable Capital",
                    data={
                        CONF_URL: url,
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional(CONF_URL, default=""): str}),
            errors=errors,
            description_placeholders={"default_url": DEFAULT_URL},
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return ScalableCapitalOptionsFlow()


class ScalableCapitalOptionsFlow(OptionsFlow):
    """Options flow: override URL (advanced) and scan interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            data = dict(self.config_entry.data)
            new_url = user_input.get(CONF_URL, "").strip().rstrip("/")
            if new_url:
                data[CONF_URL] = new_url
            try:
                interval = max(MIN_SCAN_INTERVAL, int(user_input[CONF_SCAN_INTERVAL]))
            except (TypeError, ValueError):
                interval = DEFAULT_SCAN_INTERVAL
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=data,
                options={CONF_SCAN_INTERVAL: interval},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current_url = self.config_entry.data.get(CONF_URL, DEFAULT_URL)
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=current_url): str,
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "min_interval": str(MIN_SCAN_INTERVAL),
                "default_url": DEFAULT_URL,
            },
        )
