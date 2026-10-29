#!/bin/zsh
# Doppio clic: avvia il dashboard e il cervello di Francesca, poi apre il browser.
cd "$(dirname "$0")/server" || exit 1
export ROCKY_START_BRAIN=1
(sleep 3; open "http://localhost:8766/") &
echo "Francesca si sta avviando. Lascia aperta questa finestra; chiudila (o Ctrl+C) per spegnerla."
exec .venv/bin/python launcher.py
