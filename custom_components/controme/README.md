# Controme Smart-Heat-OS Integration für Home Assistant

**⚠️ UNOFFICIAL - NOT AFFILIATED WITH CONTROME GMBH**

Diese Custom Component ermöglicht die Integration von Controme Smart-Heat-OS Heizsystemen in Home Assistant.

> **Important:** This is an unofficial community integration. Use at your own risk.  
> For official support, visit [controme.com/api](https://controme.com/api)

## Features

✅ **Climate Entities** - Jeder Raum wird als Climate Entity dargestellt mit:
- Aktueller und Ziel-Temperatur
- HVAC-Modi (Heat/Auto)
- Ventilpositionen als Attribute
- Heizbedarf-Status

✅ **System Sensoren**:
- System-Heizbedarf (durchschnittliche Ventilposition über alle Räume)
- Anzahl aktiv heizender Räume

✅ **Device Registry Integration**:
- Gateway-Device für System-Übersicht
- Room-Devices für gruppierte Anzeige
- Thermostat-Devices mit Diagnosesensoren

## Installation

### Option 1: Manuell

1. Kopiere den `custom_components/controme` Ordner in dein Home Assistant `config/custom_components/` Verzeichnis
2. Starte Home Assistant neu
3. Gehe zu **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
4. Suche nach "Controme" und folge dem Setup-Dialog

### Option 2: HACS (zukünftig)

Sobald die Integration in HACS verfügbar ist:
1. Öffne HACS
2. Suche nach "Controme Smart-Heat-OS"
3. Installiere die Integration
4. Starte Home Assistant neu

## Konfiguration

### Setup via UI

1. Gehe zu **Einstellungen** → **Geräte & Dienste**
2. Klicke auf **+ Integration hinzufügen**
3. Suche nach "Controme"
4. Gib deine Controme MiniServer Daten ein:
   - **Host**: `http://192.168.1.100` (IP deines MiniServers)
   - **Benutzername**: Dein Controme Benutzername
   - **Passwort**: Dein Controme Passwort

## Entities

### Climate Entities (pro Raum)

```yaml
climate.wohnzimmer:
  current_temperature: 21.7
  target_temperature: 21.0
  hvac_mode: auto
  attributes:
    valve_positions: [0, 0, 0, 0, 0, 0]
    average_valve_position: 0
    is_heating: false
    floor: Erdgeschoss
```

### Sensor Entities (System)

```yaml
sensor.controme_system_heating_demand:
  state: 13.4  # Prozent
  attributes:
    system_heating_demand: "Low"
    total_rooms: 7
    active_heating_rooms: 2

sensor.controme_active_heating_rooms:
  state: 2  # von 7 Räumen
```

## Update-Intervall

- **Climate Entities**: 60 Sekunden (konfigurierbar)
- **Sensor Entities**: Teilen sich das gleiche Update-Intervall
- **Coordinator**: Zentrale Datenabfrage verhindert redundante Requests

## Automatisierungsbeispiele

### Heizbedarf-basierte Steuerung

```yaml
automation:
  - alias: "Heizung bei hohem Bedarf optimieren"
    trigger:
      - platform: numeric_state
        entity_id: sensor.controme_system_heating_demand
        above: 70
    action:
      - service: notify.mobile_app
        data:
          message: "Hoher Heizbedarf: {{ states('sensor.controme_system_heating_demand') }}%"
```

### Benachrichtigung bei Heizungsaktivität

```yaml
automation:
  - alias: "Info wenn Raum heizt"
    trigger:
      - platform: state
        entity_id: climate.wohnzimmer
        attribute: is_heating
        to: true
    action:
      - service: notify.mobile_app
        data:
          message: "Wohnzimmer heizt jetzt"
```

## Bekannte Einschränkungen

⚠️ **Temperatur-Steuerung**: Aktuell nur lesend implementiert
- Das Setzen der Zieltemperatur über HA ist noch nicht umgesetzt
- Erfordert Implementierung des entsprechenden Controme API Endpoints

⚠️ **HVAC-Modi**: Nur AUTO und HEAT werden unterstützt
- OFF-Modus könnte über Preset-Modes implementiert werden

## Technische Details

### Architektur

```
custom_components/controme/
├── __init__.py              # Integration Setup
├── manifest.json            # Metadaten
├── config_flow.py           # UI Configuration
├── coordinator.py           # Data Update Coordinator
├── const.py                 # Konstanten
├── climate.py               # Climate Platform
├── sensor.py                # Sensor Platform
├── strings.json             # UI Strings (DE)
├── translations/
│   └── en.json              # UI Strings (EN)
└── controme_scraper/        # Backend Modul
    ├── heizung.py           # Main Controller
    ├── models.py            # Data Models
    ├── parsers.py           # HTML Parsers
    ├── web_client.py        # HTTP Client
    └── ...
```

### Datenfluss

1. **Coordinator** ruft alle 60s `controller.get_rooms()` auf
2. **WebClient** macht HTTP Requests an Controme AJAX Endpoints
3. **Parser** extrahieren strukturierte Daten aus HTML
4. **Models** stellen HA-optimierte Datenstrukturen bereit
5. **Entities** konsumieren Daten aus dem Coordinator

## Troubleshooting

### Verbindung fehlgeschlagen
- Prüfe ob der MiniServer erreichbar ist: `ping 192.168.1.100`
- Teste den Login im Browser: `http://192.168.1.100`
- Prüfe die Logs: **Einstellungen** → **System** → **Logs**

### Keine Räume gefunden
- Prüfe ob Räume im Controme System konfiguriert sind
- Aktiviere Debug-Logging (siehe unten)

### Debug-Logging aktivieren

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.controme: debug
    custom_components.controme.controme_scraper: debug
```

## Support

- **Issues**: https://github.com/maxibick/controme_scraper/issues
- **Dokumentation**: https://github.com/maxibick/controme_scraper

## Lizenz

MIT License - siehe LICENSE Datei

## Danksagung

Entwickelt für die Controme Smart-Heat-OS Heizungssteuerung.
