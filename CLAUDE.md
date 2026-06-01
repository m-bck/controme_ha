# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Code changes via controme-dev agent only

**All code changes in this repository must be made exclusively through the `controme-dev` agent** (`.claude/agents/controme-dev.md`).

Do not edit, create, or delete any files under `custom_components/controme/` directly as the main Claude Code instance. Always delegate development work to the `controme-dev` agent via the `Agent` tool. This applies to every change, no matter how small — including one-line fixes, constant additions, or manifest updates.

**All code analysis and research must be delegated to the `controme-analyst` agent** (`.claude/agents/controme-analyst.md`).

Do not read or grep through `custom_components/controme/` directly as the main Claude Code instance to answer questions about the codebase. Always delegate analysis, searches, architecture questions, and code reviews to the `controme-analyst` agent via the `Agent` tool.

**All release tasks must be delegated to the `controme-release` agent** (`.claude/agents/controme-release.md`).

Do not create Git tags, push releases, run linting, or perform pre-release code reviews directly as the main Claude Code instance. Always delegate these tasks to the `controme-release` agent via the `Agent` tool. This includes: version synchronization checks, changelog validation, linting, code review before releases, tag creation (`v{MAJOR}.{MINOR}.{PATCH}`), and publishing GitHub Releases.

**The main Claude Code instance is a coordinator only.** Its sole responsibilities are:
- Understanding the user's intent
- Delegating analysis tasks to `controme-analyst`
- Passing findings to `controme-dev` for implementation
- Delegating release tasks to `controme-release`
- Summarizing results back to the user

For any problem or task involving the repository, always follow this sequence:
1. **Analyse** — delegate to `controme-analyst` to understand the problem
2. **Implement** — pass the analyst's findings to `controme-dev` to make the change
3. **Release** (when applicable) — delegate to `controme-release` for tagging and publishing
4. **Report** — summarize what was done for the user

Never shortcut this flow by acting directly, even for trivial tasks.

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
