"""סנסור Hebrew Jokes."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HebrewJokesCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor."""
    coordinator: HebrewJokesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HebrewJokesSensor(coordinator, entry)], True)


class HebrewJokesSensor(CoordinatorEntity, SensorEntity):
    """סנסור שמציג בדיחה בעברית."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:emoticon-happy-outline"

    def __init__(self, coordinator: HebrewJokesCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_joke"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Hebrew Jokes",
            "manufacturer": "bdihot.co.il",
            "model": "REST Sensor",
        }

    @property
    def native_value(self) -> str | None:
        """Return the current joke."""
        if self.coordinator.data:
            return self.coordinator.data.get("joke") or None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        data = self.coordinator.data or {}
        raw = data.get("raw", {})
        attrs: dict = {}
        try:
            joke_data = raw.get("joke", {})
            if isinstance(joke_data, dict):
                for key in ("id", "title", "category", "author"):
                    val = joke_data.get(key)
                    if val:
                        attrs[key] = val
        except (AttributeError, TypeError):
            pass
        return attrs
