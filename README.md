# Controme Smart-Heat-OS - Home Assistant Integration

**UNOFFICIAL** Home Assistant integration for [Controme Smart-Heat-OS](https://www.controme.com/) heating control systems.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub release](https://img.shields.io/github/v/release/maxibick/controme_ha)
![GitHub](https://img.shields.io/github/license/maxibick/controme_ha)

> ⚠️ **DISCLAIMER**: This is an unofficial, community-developed integration. It is NOT affiliated with, endorsed by, or supported by Controme GmbH. "Controme" and "Smart-Heat-OS" are trademarks of Controme GmbH.

## Features

🌡️ **Climate Entities** - Individual thermostat control with temperature setting  
📊 **Sensors** - System metrics, temperatures, valve positions  
🔢 **Number Entities** - Configure thermostat parameters  
🔘 **Select Entities** - Choose heating modes and presets  
🔌 **Switch Entities** - Enable/disable thermostats  
🏠 **Multi-House Support** - Manage multiple houses  
🔄 **Real-time Updates** - 60-second polling interval  

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add repository URL: `https://github.com/maxibick/controme_ha`
5. Category: "Integration"
6. Click "Add"
7. Find "Controme Smart-Heat-OS" and click "Download"
8. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy `custom_components/controme` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Controme"**
4. Enter your Controme system details:
   - **Host**: IP address or hostname (e.g., `10.72.12.80` or `http://10.72.12.80`)
   - **Username**: Your Controme username
   - **Password**: Your Controme password
   - **House ID**: (Optional) Default is 1

## Entities

### Climate Entities (Thermostats)

Each thermostat appears as a climate entity with:
- Current and target temperature
- Heating status (heating/idle)
- Icon changes based on state (🔥/🌡️)
- Temperature control (0.5°C steps, 5-30°C range)

**Attributes:**
- Device ID, MAC address
- Room and floor assignment
- Valve positions and averages
- Firmware version
- All 12 thermostat configuration options

### Sensor Entities

- **System Heating Demand** - Overall heating load (%)
- **Active Rooms** - Number of rooms currently heating
- **Boiler Status** - On/Off state
- **Temperature Sensors** - All configured sensors
- **Humidity Sensors** - If available

### Number Entities

Configure thermostat parameters:
- Display brightness (0-30)
- Temperature offset (-5 to +5°C)
- Various timing and control parameters

### Select Entities

- Heating modes
- Presets (if configured)

### Switch Entities

- Enable/disable individual thermostats

## Python API Library

This integration uses the [`controme-scraper`](https://github.com/m-bck/controme-scraper) Python library, available on PyPI:

```bash
pip install controme-scraper
```

You can use this library independently for automation scripts, monitoring, or other projects.

## Multi-House Support

If your Controme system manages multiple houses, add separate integrations with different House IDs:
- House 1: House ID = 1
- House 2: House ID = 2

Each will appear as a separate integration with its own entities.

## Automation Example

```yaml
automation:
  - alias: "Morning Warmup"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.wohnzimmer_thermostat
        data:
          temperature: 22
```

## Troubleshooting

### Integration won't load
- Check Home Assistant logs for errors
- Verify network connectivity to Controme system
- Ensure credentials are correct

### Entities not updating
- Check "Last Update Success" in integration details
- Verify Controme system is online
- Check firewall settings

### Can't set temperature
- Ensure thermostat is assigned to a room in Controme
- Check thermostat is enabled
- Verify user has write permissions

## Legal Notice

This integration accesses the **local web interface** of your Controme heating control system. It does NOT use any official API.

**Use at your own risk.** The authors are not responsible for:
- Damage to your heating system
- Incorrect temperature settings
- Data loss or corruption
- Warranty violations

**Recommended:** Use only for personal, non-commercial purposes in your own home.

For official API access, contact: [Controme GmbH](https://controme.com/api)

## Contributing

Contributions are welcome! Please open an issue or pull request.

## Links

- **GitHub Repository (Integration)**: https://github.com/maxibick/controme_ha
- **Python Library (PyPI)**: https://github.com/m-bck/controme-scraper
- **Home Assistant**: https://www.home-assistant.io/
- **Controme Official Website**: https://www.controme.com/
- **Controme Official API**: https://controme.com/api

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Disclaimer:** This project is not affiliated with, endorsed by, or supported by Controme GmbH or Home Assistant. All trademarks are property of their respective owners.
