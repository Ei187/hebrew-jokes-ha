"""סנסור Hebrew Jokes."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HebrewJokesCoordinator
from .const import DOMAIN

# המגבלה של Home Assistant לאורך state
MAX_STATE_LENGTH = 255


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor."""
    coordinator: HebrewJokesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HebrewJokesSensor(coordinator, entry)], True)


class HebrewJokesSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
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
        self._restored_joke: str | None = None

    async def async_added_to_hass(self) -> None:
        """שחזור הבדיחה האחרונה אחרי ריסטארט."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        # מעדיפים את הבדיחה המלאה מהמאפיין, ואם אין - את ה-state
        restored = last_state.attributes.get("joke") or last_state.state
        if restored and restored not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._restored_joke = restored

    def _current_joke(self) -> str | None:
        """הבדיחה המלאה הנוכחית (מהקורדינטור, ואם אין - המשוחזרת)."""
        if self.coordinator.data:
            joke = self.coordinator.data.get("joke")
            if joke:
                return joke
        return self._restored_joke

    @property
    def native_value(self) -> str | None:
        """Return the joke, shortened to fit the 255-char state limit."""
        joke = self._current_joke()
        if not joke:
            return None
        if len(joke) <= MAX_STATE_LENGTH:
            return joke
        return joke[: MAX_STATE_LENGTH - 1].rstrip() + "…"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes, including the full joke text."""
        attrs: dict = {}

        joke = self._current_joke()
        if joke:
            attrs["joke"] = joke

        data = self.coordinator.data or {}
        raw = data.get("raw", {})
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
