# Changelog

All notable changes to the Controme Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-06-01

### Security
- Config flow now warns when a plain HTTP host is entered. Credentials are sent unencrypted over HTTP; the warning interrupts the flow and asks the user to confirm or switch to HTTPS before proceeding.

### Changed
- Added `http_insecure_warning` error string to `strings.json`.
- Extended `.gitignore` with common secrets patterns (`.env`, `*.key`, `*.pem`, `credentials.json`).

## [1.1.0] - 2026-06-01

### Fixed
- `AttributeError` when `coordinator.data` is `None` on first startup after a failed poll. All platforms (`climate`, `sensor`, `number`, `select`, `switch`) now guard every access to `coordinator.data` with a `None` check before calling `.get()`.

## [1.0.0] - 2025-11-17

### Added
- Initial release of Home Assistant integration
- Climate entities for all thermostats with temperature control
- Sensor entities for system metrics and individual sensors
- Number entities for thermostat configuration
- Select entities for heating modes
- Switch entities for enabling/disabling thermostats
- Multi-house support via House ID parameter
- URL normalization in config flow (auto-add http://)
- Async executor for blocking I/O operations
- Legal disclaimers and trademark notices

### Changed
- Switched from embedded library to PyPI package `controme-scraper>=0.1.0`
- Improved config flow with better error handling
- Enhanced entity attributes with complete thermostat configuration

### Fixed
- Blocking call errors in event loop during controller initialization
- URL validation when protocol prefix is missing
- Import paths updated for external package dependency

### Technical
- **Dependency**: Now uses `controme-scraper` from PyPI
- **Min HA Version**: 2024.1.0
- **Python Version**: 3.10+

## Repository Split

This is the first release of the separated Home Assistant integration repository.
Previously, both the Python library and HA integration were in one repository.

- **Python Library**: https://github.com/m-bck/controme-scraper (PyPI: `controme-scraper`)
- **HA Integration**: https://github.com/maxibick/controme_ha (this repository)
