"""אינטגרציה Hebrew Jokes ל-Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL, API_URL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hebrew Jokes from a config entry."""
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = HebrewJokesCoordinator(hass, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload on options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class HebrewJokesCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches jokes from bdihot.co.il."""

    def __init__(self, hass: HomeAssistant, scan_interval: int) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._last_joke: str = ""

    async def _async_update_data(self) -> dict:
        """Fetch joke from bdihot.co.il."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(API_URL) as resp:
                        if resp.status != 200:
                            _LOGGER.warning(
                                "bdihot.co.il החזיר סטטוס %s", resp.status
                            )
                            return {"joke": self._last_joke}

                        data = await resp.json(content_type=None)

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"שגיאת רשת: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"שגיאה: {err}") from err

        # אותו לוגיקה כמו ה-value_template המקורי
        try:
            content = data.get("joke", {}).get("content", "")
            content = content.replace("\r", "").replace("\n", " ").strip()
        except (AttributeError, TypeError):
            content = ""

        if content and content.lower() != "none":
            self._last_joke = content

        return {
            "joke": self._last_joke,
            "raw": data,
        }
