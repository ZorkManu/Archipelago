# Archipelago Client für Die Siedler

Dieser Client ermöglicht die Verbindung zwischen dem Spiel "Die Siedler" und dem Archipelago Multiplayer-System. Er synchronisiert Locations und Items zwischen dem Spiel und dem Archipelago-Server.

## Dateien

- `gdb_reader.py` - Liest und schreibt in die GDB.bin Datei des Spiels
- `archipelago_client.py` - Hauptclient für die Verbindung zum Archipelago-Server
- `locations.py` - Verwaltet die Locations für Archipelago
- `items.py` - Verwaltet die Items für Archipelago

## Installation

1. Stellen Sie sicher, dass Python 3.6 oder höher installiert ist
2. Kopieren Sie alle Dateien in einen Ordner namens `ArchipelagoTools`
3. Führen Sie `archipelago_client.py` aus

## Verwendung

### Verbindung zum Server

```python
from archipelago_client import ArchipelagoClient

client = ArchipelagoClient(
    server_address="archipelago.gg",
    port=38281,
    game_name="Die Siedler",
    player_name="IhrName",
    password=None  # Optional: Passwort für den Raum
)

if client.connect():
    print("Verbunden mit Archipelago Server")
    # Hauptschleife hier
else:
    print("Verbindung fehlgeschlagen")
```

### Befehle

- `sync` - Synchronisiert mit der GDB
- `locations` - Zeigt alle erreichten Locations an
- `items` - Zeigt alle erhaltenen Items an
- `location <id>` - Sendet eine erreichte Location an den Server
- `item <id> <location_id> <player>` - Sendet ein Item an einen anderen Spieler
- `exit` - Beendet das Programm

## GDB-Integration

Der Client speichert Locations und Items in der GDB.bin Datei mit folgenden Schlüsseln:

- `archipelago_location_<id>` - Für erreichte Locations
- `archipelago_item_<id>` - Für erhaltene Items

## Anpassung

### Locations hinzufügen

```python
from locations import Locations

locations = Locations()
locations.add_location(10001, "Erste Mission")
locations.add_location(10002, "Zweite Mission")
locations.save_to_file("locations.csv")
```

### Items hinzufügen

```python
from items import Items

items = Items()
items.add_item(20001, "Schwert")
items.add_item(20002, "Bogen")
items.save_to_file("items.csv")
```

## Fehlerbehebung

- **Verbindungsfehler**: Stellen Sie sicher, dass der Server erreichbar ist und der Port korrekt ist
- **GDB-Fehler**: Stellen Sie sicher, dass das Spiel nicht läuft, wenn Sie die GDB bearbeiten
- **Paketfehler**: Überprüfen Sie die Protokollversion und die Paketformate

## Lizenz

Dieser Code ist unter der MIT-Lizenz lizenziert. 