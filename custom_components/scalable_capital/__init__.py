"""Scalable Capital integration for Home Assistant."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_SCAN_INTERVAL, CONF_URL, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import ScalableCapitalClient, ScalableCapitalCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (config-flow only)."""
    return True


async def _get_scan_interval(entry: ConfigEntry) -> timedelta:
    interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    try:
        seconds = max(300, int(interval))
    except (TypeError, ValueError):
        seconds = DEFAULT_SCAN_INTERVAL
    return timedelta(seconds=seconds)


async def _resolve_scan_interval(client, entry: ConfigEntry) -> timedelta:
    """Add-on option wins; the integration option is the fallback."""
    addon_seconds = await client.async_get_scan_interval()
    if addon_seconds:
        _LOGGER.info("Intervallo di aggiornamento dall'add-on: %s s", addon_seconds)
        return timedelta(seconds=addon_seconds)
    return await _get_scan_interval(entry)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scalable Capital from a config entry."""
    client = ScalableCapitalClient(
        hass,
        url=entry.data[CONF_URL],
    )
    coordinator = ScalableCapitalCoordinator(
        hass,
        client=client,
        config_entry=entry,
        update_interval=await _resolve_scan_interval(client, entry),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)