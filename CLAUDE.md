# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A custom Home Assistant integration for Controme Smart-Heat-OS heating systems. It is distributed via HACS and installed by copying `custom_components/controme/` into a Home Assistant instance. There are no build steps or tests — development means editing Python files and reloading the integration in HA.

## Development workflow

To test changes, copy the `custom_components/controme/` directory to your HA instance's `config/custom_components/` and restart HA (or use Developer Tools → YAML → Reload All Integrations for minor changes).

The integration depends on the [`controme-scraper`](https://github.com/m-bck/controme-scraper) PyPI library (`controme_scraper`). Install it locally for IDE support:

```bash
pip install controme-scraper
```

## Architecture

All data flows through `coordinator.py` (`ContromeDataUpdateCoordinator`), which polls the Controme system every 60 seconds via `controme_scraper.controller.ContromeController`. The coordinator stores a dict with keys `thermostats`, `gateway`, and `sensors`.

Each platform (`climate.py`, `sensor.py`, `number.py`, `select.py`, `switch.py`) reads from that coordinator dict. Entities are thermostat-based (keyed by thermostat device ID / MAC), not room-based — `__init__.py` includes a migration step that removes old `controme_room_*` entities on startup.

The `ContromeController` is synchronous (HTTP scraping), so all calls to it must be wrapped in `hass.async_add_executor_job(...)`.

## Key files

| File | Purpose |
|------|---------|
| `const.py` | All constants, scan interval, platform list |
| `coordinator.py` | Data fetching and caching |
| `config_flow.py` | UI config flow (host, username, password, house_id) |
| `__init__.py` | Entry setup/teardown and entity migration |
| `manifest.json` | Integration metadata and `controme-scraper` version requirement |

## Adding a new entity type

1. Create `<platform>.py` following the pattern of an existing platform.
2. Add the platform string to `PLATFORMS` in `const.py`.
3. Add any new constants to `const.py`.

## Versioning

Bump `version` in `manifest.json` and add an entry to `CHANGELOG.md` before tagging a release.
