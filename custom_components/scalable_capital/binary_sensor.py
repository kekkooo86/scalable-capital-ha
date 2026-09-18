"""Binary sensors for the Scalable Capital integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_URL, DOMAIN
from .coordinator import ScalableCapitalCoordinator


class ScalableBridgeOnlineSensor(BinarySensorEntity):
    """Bridge and broker session reachability."""

    _attr_has_entity_name = True
    _attr_unique_id = "scalable_capital_online"
    _attr_translation_key = "bridge_online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:check-network"

    def __init__(self, coordinator: ScalableCapitalCoordinator) -> None:
        self.coordinator = coordinator
        self.entity_id = "binary_sensor.scalable_capital_sc_bridge_online"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.data[CONF_URL])},
            "name": "Scalable Capital",
            "manufacturer": "Scalable Capital",
            "model": "sc-bridge",
            "configuration_url": coordinator.config_entry.data[CONF_URL],
        }

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    coordinator: ScalableCapitalCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ScalableBridgeOnlineSensor(coordinator)])