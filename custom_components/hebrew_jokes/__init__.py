"""אינטגרציה Hebrew Jokes ל-Home Assistant."""
from __future__ import annotations

import html
import logging
import re
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

# כשהבדיחה לא תקינה: מנסים שוב כל כך הרבה שניות, עד שמתקבלת תקינה
_RETRY_DELAY = 10

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant HebrewJokes)",
    "Accept": "application/json, text/plain, */*",
}

_TAG_RE = re.compile(r"<[^>]+>")


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
    """Coordinator that fetches jokes from bdihot.co.il.

    On a bad/empty joke it keeps the previous value (never unavailable) and
    retries every _RETRY_DELAY seconds until a good joke arrives, then returns
    to the normal scan interval.
    """

    def __init__(self, hass: HomeAssistant, scan_interval: int) -> None:
        """Initialize."""
        self._normal_interval = timedelta(seconds=scan_interval)
        self._retry_interval = timedelta(seconds=_RETRY_DELAY)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._normal_interval,
        )

    @staticmethod
    def _clean_content(raw_content: str) -> str:
        """מסיר תגי HTML (כמו <p></p>) ומפענח ישויות HTML, ומחזיר טקסט נקי בשורה אחת."""
        text = _TAG_RE.sub(" ", raw_content)  # מסיר <p>, </p> וכל תג אחר
        text = html.unescape(text)  # &quot; &amp; וכו' -> " & וכו'
        text = text.replace("\r", " ").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def _fetch_once(self) -> tuple[str, dict]:
        """ניסיון בודד להביא בדיחה. לעולם לא זורק - מחזיר ("", {}) בכישלון."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession(headers=_HEADERS) as session:
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
            raw_content = data.get("joke", {}).get("content", "")
        except (AttributeError, TypeError):
            _LOGGER.warning("מבנה תשובה לא צפוי מה-API: %s", str(data)[:200])
            raw_content = ""

        content = self._clean_content(raw_content)

        if content and content.lower() not in ("none", "unknown", "unavailable"):
            return content, data

        _LOGGER.warning("התקבל תוכן ריק/לא תקין מה-API: %s", str(data)[:200])
        return "", data

    async def _async_update_data(self) -> dict:
        """Fetch a joke; on failure keep the previous one and retry soon."""
        content, raw = await self._fetch_once()

        if content:
            # הצלחה - חוזרים לקצב הרגיל
            self.update_interval = self._normal_interval
            return {"joke": content, "raw": raw}

        # כישלון - מנסים שוב בקרוב, ובינתיים משאירים את הבדיחה הקודמת
        self.update_interval = self._retry_interval
        if self.data:
            return self.data
        return {"joke": None, "raw": {}}
