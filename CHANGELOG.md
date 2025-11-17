# Changelog

All notable changes to the Controme Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- **Python Library**: https://github.com/maxibick/controme_scraper (PyPI: `controme-scraper`)
- **HA Integration**: https://github.com/maxibick/controme_ha (this repository)
