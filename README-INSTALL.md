# Sysadmin Gym 3.2.0 — installatie en updates

## Eerste installatie (eenmalig)

1. Maak een backup van je VM-directory: `cp -a ~/linux-gym-v3 ~/linux-gym-v3-backup`.
2. Pak `sysadmin-gym-v3.2.0-updatable.tar.gz` uit in je home-directory: `tar -xzf ~/Downloads/sysadmin-gym-v3.2.0-updatable.tar.gz -C ~`.
3. `cd ~/sysadmin-gym && ./gym.sh list && ./gym.sh start`.

De meegeleverde archiefinhoud is gebaseerd op je geüploade directory. Let op: deze eerste migratie neemt alleen de opgeslagen bestanden uit die upload mee; lokale wijzigingen sinds de upload moet je zelf veiligstellen. **Pak latere releases niet opnieuw over de volledige directory uit.**

## Dagelijks

`./gym.sh start`, `./gym.sh hint 1`, `./gym.sh check`, `./gym.sh reset`, `./gym.sh stats`.

## Nieuwe oefenmoduleversie installeren

Een updatebestand bevat uitsluitend `manifest.json` en `tasks.json`.

```bash
./gym.sh install ~/Downloads/sysadmin-gym-network-3.2.1.tar.gz
./gym.sh list
```

Een module-installatie controleert de versie, compatibiliteit, ID-conflicten en veiligheid van het archief. De vorige module wordt opgeslagen in `module-backups/`. De installer past **nooit** `gym-config.json`, `history/`, `progress.json`, `backups/`, `session.json` of `workspace/` aan. Update niet tijdens een actieve sessie.

Terugdraaien: `./gym.sh rollback network`.

Een geheel nieuwe module moet ook als entry in `gym-config.json` worden gezet, bijvoorbeeld `{"name":"nieuw","enabled":true,"count":1,"every":2}`. Alleen bestaande opdrachtsoorten kunnen met een module-update worden toegevoegd: een geheel nieuwe controle-/voorbereidingsmethode vereist een engine-update.

## Engine-updates

De module-installer ondersteunt **module-updates**, geen willekeurige code-/engine-updates. Engine-updates moeten apart worden uitgebracht als gecontroleerde migraties die de runtime-data intact laten; dat mechanisme is nog niet geïmplementeerd. Python 3 en voor TLS OpenSSL zijn vereist.
