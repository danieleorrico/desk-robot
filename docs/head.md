# La testa web (telefono, portatile, qualsiasi browser)

`server/brain/head.py` + `server/brain/head.html`: una pagina che fa da corpo del robot. Occhi ed emozioni sullo
schermo, microfono = orecchio, altoparlante = voce, fotocamera (opzionale) = occhio. Parla lo stesso protocollo del
robot vero (`docs/protocol.md`): il cervello non nota la differenza. Un solo "robot" alla volta (vero o testa web).

## Provarla sul computer del cervello
1. Avvia il cervello (launcher o doppio clic). Nel log compare `web head: http://...:8768/`.
2. Apri http://localhost:8768/ , tocca **Sveglia**, consenti il microfono.
3. Di' "Ehi Francesca, come stai?". Il microfono e la voce ora sono quelli del browser.

## Dal telefono o da un altro computer
- Serve HTTPS (i browser bloccano il microfono su http:// fuori da localhost) e `ROCKY_REMOTE_ACCESS=tailscale` (o `lan`).
- Certificato gratuito con Tailscale (una volta sola):
  1. Console Tailscale → DNS → attiva MagicDNS e "HTTPS certificates".
  2. Sul server: `sudo tailscale cert --cert-file /opt/desk-robot/server/certs/head.crt --key-file /opt/desk-robot/server/certs/head.key NOME.tailXXXX.ts.net`
  3. In `server/.env`: `HEAD_TLS_CERT=certs/head.crt` e `HEAD_TLS_KEY=certs/head.key`, poi riavvia il cervello.
  4. Sul telefono (con l'app Tailscale accesa) apri `https://NOME.tailXXXX.ts.net:8768/`.
- Il certificato dura 90 giorni: rinnova ripetendo il comando del punto 2.

## Sicurezza
- Risponde solo al computer stesso, oppure ai dispositivi Tailscale / LAN secondo `ROCKY_REMOTE_ACCESS`.
- Il token del robot resta sul server (`ROBOT_TOKEN`): il browser non lo vede mai.
- Una pagina di un altro sito non può collegarsi (controllo di Origin e Host).
- La fotocamera è spenta finché non tocchi il pulsante: le immagini vanno al fornitore dell'IA come per il robot vero.

## Limiti della prima versione
- Lo schermo deve restare acceso (la pagina lo chiede al telefono) e il telefono in carica.
- Il volto è disegnato dalla pagina: non usa ancora i "face pack" del progetto.
- Nessun movimento di testa: pan e tilt spostano solo lo sguardo.
