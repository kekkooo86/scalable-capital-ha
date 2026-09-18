"""Coordinator and read-only client for the Scalable Capital integration.

Polls the local sc-bridge HTTP API (read-only wrapper around the `sc` CLI).
"""

import logging
from datetime import datetime, timedelta, timezone

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BRIDGE_PERFORMANCE_TIMEFRAMES, DOMAIN, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ScalableCapitalClient:
    """Minimal HTTP client for the read-only bridge API."""

    def __init__(self, hass: HomeAssistant, url: str) -> None:
        self._url = url.rstrip("/")
        self._session = async_get_clientsession(hass)

    @property
    def url(self) -> str:
        """Bridge base URL."""
        return self._url

    async def _get_json(self, path: str) -> dict:
        try:
            async with self._session.get(
                f"{self._url}{path}",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Bridge ha risposto HTTP {resp.status} su {path}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Errore di rete verso {self._url}{path}: {err}") from err
        except (ValueError, TypeError) as err:
            raise UpdateFailed(f"Risposta non valida da {path}: {err}") from err

    async def async_get_scan_interval(self) -> int | None:
        """Read the polling interval (seconds) suggested by the bridge."""
        try:
            data = await self._get_json("/config")
        except UpdateFailed:
            return None
        if not data.get("ok"):
            return None
        try:
            seconds = int(data.get("scan_interval"))
        except (TypeError, ValueError):
            return None
        return max(MIN_SCAN_INTERVAL, seconds)

    async def async_fetch(self) -> dict:
        """Fetch the portfolio overview."""
        portfolio = await self._get_json("/portfolio")
        if not portfolio.get("ok"):
            raise UpdateFailed(str(portfolio.get("error", "sc-bridge /portfolio fallito")))
        return {"portfolio": portfolio}


class ScalableCapitalCoordinator(DataUpdateCoordinator):
    """Fetch and normalize the Scalable Capital portfolio state."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ScalableCapitalClient,
        config_entry: ConfigEntry,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=config_entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        interval = await self.client.async_get_scan_interval()
        if interval:
            new_interval = timedelta(seconds=interval)
            if self.update_interval != new_interval:
                self.update_interval = new_interval
                _LOGGER.info(
                    "Intervallo di aggiornamento impostato dall'add-on: %s s", interval
                )
        raw = await self.client.async_fetch()
        return self._normalize(raw["portfolio"])

    @staticmethod
    def _normalize(portfolio: dict) -> dict:
        overview = portfolio.get("overview", {}) or {}
        valuation = overview.get("valuation", {}) or {}

        performance = {}
        for entry in overview.get("performance", []) or []:
            timeframe = BRIDGE_PERFORMANCE_TIMEFRAMES.get(entry.get("timeframe"))
            if timeframe:
                performance[timeframe] = entry.get("simpleAbsoluteReturn")

        total = valuation.get("total")
        securities = valuation.get("securities")
        cash = None
        if total is not None and securities is not None:
            cash = round(max(0.0, total - securities), 2)
        if total is not None:
            total = round(total, 2)
        if securities is not None:
            securities = round(securities, 2)

        return {
            "portfolio_value": total,
            "securities_total": securities,
            "cash": cash,
            "performance": performance,
            "generated_at": (overview.get("timestamps", {}) or {}).get(
                "valuation_timestamp_utc"
            ),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }