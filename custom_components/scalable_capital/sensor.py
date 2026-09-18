"""Sensors for the Scalable Capital integration."""

import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import ConfigType

from .const import CONF_URL, DOMAIN
from .coordinator import ScalableCapitalCoordinator

_PERFORMANCE_ENTITY_IDS = {
    "today": "scalable_capital_plus_minusvalenza_oggi",
    "week": "scalable_capital_plus_minusvalenza_settimana",
    "month": "scalable_capital_plus_minusvalenza_mese",
    "year": "scalable_capital_plus_minusvalenza_anno",
    "total": "scalable_capital_plus_minusvalenza_totale",
}


class ScalableBaseEntity(CoordinatorEntity, SensorEntity):
    """Base entity sharing the Scalable Capital device."""

    _attr_has_entity_name = True
    _entity_id: str | None = None

    def __init__(self, coordinator: ScalableCapitalCoordinator) -> None:
        super().__init__(coordinator)
        if self._entity_id:
            self.entity_id = f"sensor.{self._entity_id}"
        entry = coordinator.config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_URL])},
            "name": "Scalable Capital",
            "manufacturer": "Scalable Capital",
            "model": "sc-bridge",
            "configuration_url": entry.data[CONF_URL],
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class ScalablePortfolioSensor(ScalableBaseEntity):
    """Total portfolio value in EUR."""

    _attr_unique_id = "scalable_capital_portfolio_total"
    _entity_id = "scalable_capital_portafoglio_scalable"
    _attr_translation_key = "portfolio"
    _attr_icon = "mdi:finance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.get("portfolio_value") if data else None


class ScalableSecuritiesSensor(ScalableBaseEntity):
    """Total value of securities (excludes cash)."""

    _attr_unique_id = "scalable_capital_held_total"
    _entity_id = "scalable_capital_titoli_scalable"
    _attr_translation_key = "securities"
    _attr_icon = "mdi:briefcase"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.get("securities_total") if data else None


class ScalableCashSensor(ScalableBaseEntity):
    """Available cash in EUR."""

    _attr_unique_id = "scalable_capital_cash"
    _entity_id = "scalable_capital_cash_scalable"
    _attr_translation_key = "cash"
    _attr_icon = "mdi:cash"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.get("cash") if data else None


class ScalablePerformanceSensor(ScalableBaseEntity):
    """Absolute portfolio return for a timeframe (EUR)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:chart-line"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: ScalableCapitalCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._perf_key = key
        self._attr_unique_id = f"scalable_capital_return_{key}"
        self._attr_translation_key = f"performance_{key}"
        if key in _PERFORMANCE_ENTITY_IDS:
            self.entity_id = f"sensor.{_PERFORMANCE_ENTITY_IDS[key]}"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("performance", {}).get(self._perf_key)


class ScalableLastUpdateSensor(ScalableBaseEntity):
    """Valuation timestamp from the broker."""

    _attr_unique_id = "scalable_capital_last_update"
    _entity_id = "scalable_capital_ultimo_aggiornamento_portafoglio"
    _attr_translation_key = "last_update"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime.datetime | None:
        data = self.coordinator.data
        if not data:
            return None
        generated = data.get("generated_at")
        if not generated:
            return None
        try:
            return datetime.datetime.fromisoformat(generated.replace("Z", "+00:00"))
        except ValueError:
            return None


def build_entities(
    coordinator: ScalableCapitalCoordinator, known: set[str]
) -> list[SensorEntity]:
    """Build all sensors not yet registered, updating `known`."""
    entities: list[SensorEntity] = []

    fixed_classes = (
        ScalablePortfolioSensor,
        ScalableSecuritiesSensor,
        ScalableCashSensor,
        ScalableLastUpdateSensor,
    )
    for cls in fixed_classes:
        entity = cls(coordinator)
        if entity.unique_id not in known:
            known.add(entity.unique_id)
            entities.append(entity)

    for perf_key in ("today", "week", "month", "year", "total"):
        entity = ScalablePerformanceSensor(coordinator, perf_key)
        if entity.unique_id not in known:
            known.add(entity.unique_id)
            entities.append(entity)

    return entities


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Legacy YAML setup hook (not used, kept for safety)."""
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: ScalableCapitalCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    known: set[str] = set()

    async_add_entities(build_entities(coordinator, known))

    def _discover() -> None:
        new_entities = build_entities(coordinator, known)
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_discover)