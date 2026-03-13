# 😄 Hebrew Jokes — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/release/Ei187/hebrew-jokes-ha.svg)](https://github.com/Ei187/hebrew-jokes-ha/releases)
[![License](https://img.shields.io/github/license/Ei187/hebrew-jokes-ha.svg)](LICENSE)
[![Validate](https://github.com/Ei187/hebrew-jokes-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/Ei187/hebrew-jokes-ha/actions/workflows/validate.yml)

A Home Assistant custom integration that fetches random Hebrew jokes from [bdihot.co.il](https://www.bdihot.co.il) and exposes them as a sensor entity.

---

## ✨ Features

- 🔄 Auto-refreshes jokes at a configurable interval
- 💾 Preserves the last joke if the API returns empty
- 🖥️ Full UI setup via Config Flow (no YAML needed)
- 🌍 Supports Hebrew and English translations
- ⚙️ Adjustable update interval via Options Flow

---

## 📦 Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three dots menu → **Custom repositories**
3. Add `https://github.com/Ei187/hebrew-jokes-ha` with category **Integration**
4. Search for **Hebrew Jokes** and click **Download**
5. Restart Home Assistant

### Manual

1. Download the latest release from [Releases](https://github.com/Ei187/hebrew-jokes-ha/releases)
2. Copy the `custom_components/hebrew_jokes` folder to your HA `config/custom_components/` directory
3. Restart Home Assistant

---

## ⚙️ Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Hebrew Jokes**
3. Set the update interval in seconds (default: 500)

---

## 🔧 Sensor

| Attribute | Description |
|-----------|-------------|
| `state` | The current joke text |
| `id` | Joke ID from the API |
| `category` | Joke category |
| `title` | Joke title (if available) |

---

## 💡 Automation Examples

**Send a joke via notification to phone:**
```yaml
automation:
  - alias: "Send Joke to Phone"
    trigger:
      - platform: state
        entity_id: sensor.hebrew_jokes
    action:
      - service: notify.mobile_app_YOUR_PHONE_NAME
        data:
          title: "😂"
          message: "{{ states('sensor.hebrew_jokes') }}"
```

**Announce a joke via TTS:**
```yaml
automation:
  - alias: Announce Hebrew Joke
    trigger:
      - platform: state
        entity_id: sensor.hebrew_jokes
    action:
      - service: tts.google_translate_say
        data:
          entity_id: media_player.living_room
          message: "{{ states('sensor.hebrew_jokes') }}"
```

**Lovelace card:**
```yaml
type: markdown
content: |
  ## 😄 Joke of the moment
  {{ states('sensor.hebrew_jokes') }}
```

---

## 🏗️ Technical Details

Built with:
- Python `asyncio` / `aiohttp` for non-blocking HTTP requests
- Home Assistant `DataUpdateCoordinator` pattern for efficient polling
- `ConfigFlow` + `OptionsFlow` for full UI-based configuration
- HACS & hassfest CI validation via GitHub Actions

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
