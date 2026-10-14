# Module liegen jetzt im Drive (single source of truth)

> Stand 30.06.2026: Die lokalen Modul-Quellen unter `module-installs/` wurden bewusst entfernt.
> Es gibt ab jetzt **eine** Quelle der Wahrheit für alle CEO-GPT-Module: das **Shared Drive Fulfillment → Module**.

## Wo die Module jetzt liegen

Im Shared Drive **Fulfillment**, Ordner **Module** (und Unterordner „Module-noch nicht public" und „Modulbibliothek"), jeweils als versioniertes ZIP. Der lebende Überblick steht im gebrandeten Google Doc „CEO-GPT · Modul-Katalog" (Link in `CLAUDE.md`, Abschnitt Modul-Katalog).

## Ein Modul installieren oder bearbeiten

1. Das ZIP des Moduls aus dem Drive holen (Fulfillment → Module).
2. Entpacken.
3. Der `INSTALL.md` im Modul folgen (sie ist für Claude Code geschrieben und führt Schritt für Schritt).
4. Geheimnisse werden dabei nie von Hand in die `.env` getippt, sondern verdeckt über `python scripts/set_secret.py KEY` gesetzt (harmlose Werte mit `--show`).

## Warum lokal entfernt

Die lokalen Kopien und die Drive-ZIPs konnten auseinanderlaufen. Mit nur noch einer Ablage (Drive) ist immer klar, was der aktuelle Stand ist. Die alten lokalen Stände bleiben über die Git-Historie wiederherstellbar, falls je nötig.
