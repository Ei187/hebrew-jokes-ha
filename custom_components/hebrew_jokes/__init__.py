"""אינטגרציה Hebrew Jokes ל-Home Assistant."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import timedelta

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL, API_URL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# כמה בדיחות תקינות אחרונות לשמור כרשת ביטחון
_HISTORY_SIZE = 5

# כל עוד מעולם לא התקבלה בדיחה תקינה: כמה ניסיונות ובאיזה מרווח, לפני שמוותרים למחזור הזה
_FIRST_JOKE_MAX_RETRIES = 10
_FIRST_JOKE_RETRY_DELAY = 3  # שניות


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
    """Coordinator that fetches jokes from bdihot.co.il — never surfaces as unavailable."""

    def __init__(self, hass: HomeAssistant, scan_interval: int) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        # רשימת הבדיחות התקינות האחרונות - האחרונה שבפנים היא הכי חדשה
        self._joke_history: deque[str] = deque(maxlen=_HISTORY_SIZE)

    async def _fetch_once(self) -> tuple[str, dict]:
        """ניסיון בודד להביא בדיחה. לעולם לא זורק - מחזיר ("", {}) בכישלון."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(API_URL) as resp:
                        if resp.status != 200:
                            _LOGGER.warning(
                                "bdihot.co.il החזיר סטטוס %s", resp.status
                            )
                            return "", {}
                        data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("שגיאת רשת בשליפת בדיחה: %s", err)
            return "", {}
        except Exception as err:  # noqa: BLE001 - בכוונה, לא רוצים נפילה
            _LOGGER.warning("שגיאה בשליפת בדיחה: %s", err)
            return "", {}

        try:
            content = data.get("joke", {}).get("content", "")
            content = content.replace("\r", "").replace("\n", " ").strip()
        except (AttributeError, TypeError):
            content = ""

        if content and content.lower() != "none":
            return content, data
        return "", data

    async def _async_update_data(self) -> dict:
        """Fetch joke. If a good joke was never received yet, keep retrying quietly
        (without publishing anything) until one arrives or we run out of attempts
        for this cycle — the next scheduled cycle will try again."""
        have_history = bool(self._joke_history)
        attempts = 1 if have_history else _FIRST_JOKE_MAX_RETRIES
        last_raw: dict = {}

        for attempt in range(attempts):
            content, raw = await self._fetch_once()
            last_raw = raw
            if content:
                self._joke_history.append(content)
                return {"joke": content, "raw": raw}
            if attempt < attempts - 1:
                await asyncio.sleep(_FIRST_JOKE_RETRY_DELAY)

        # הניסיון/ים הזה נכשלו
        if self._joke_history:
            # יש היסטוריה - מציגים את הבדיחה התקינה האחרונה
            return {"joke": self._joke_history[-1], "raw": last_raw}
        # אין שום בדיחה תקינה עדיין - לא מציגים כלום, ומחכים למחזור הבא
        return {"joke": None, "raw": last_raw}
