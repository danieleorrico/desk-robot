"""Head: the robot's body as a web page (phone, tablet, laptop, any browser).

Open https://<this-computer>:8768/ on the device, tap "Wake", and it becomes the robot: its screen shows the
face, its microphone is the robot's ear, its speaker plays the voice, and its camera (if you switch it on) is the
eye. It speaks the same protocol as the real robot (docs/protocol.md), so the brain doesn't know the difference.

How it's wired: the page talks to this small server on HEAD_PORT; this server serves the page and relays the
WebSocket to the brain's robot port on the same machine, adding the robot token itself. The browser never sees
ROBOT_TOKEN. The brain's own robot port stays as it was (the real robot keeps working; one robot at a time).

Who is let in (same rules as the launcher's dashboard):
  - this computer only, unless ROCKY_REMOTE_ACCESS is "tailscale" (your Tailscale devices) or "lan" (also your home
    network). The internet is never answered.
  - the page's Host name must be one of ours, and a WebSocket must come from our own page (Origin = Host), so a
    web page on another site can't make your browser talk to the robot port.

Microphones need a secure page: http://localhost works on the computer itself, but a phone needs https://. Give it
a certificate (for example `tailscale cert <name>.ts.net`) in HEAD_TLS_CERT / HEAD_TLS_KEY (server/.env).
"""

from __future__ import annotations

import asyncio
import json
import os
import ssl
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlsplit

import websockets
from websockets.datastructures import Headers
from websockets.http11 import Response

from . import config

PAGE = Path(__file__).with_name("head.html")
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def _hostname(host_header: str) -> str:
    """'phone.tail1.ts.net:8768' / '[::1]:8768' / '192.168.1.5' → the bare, lower-case name."""
    h = (host_header or "").strip().lower()
    if h.startswith("["):
        return h[1:].split("]", 1)[0]
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


def _client_ok(addr: str) -> bool:
    if config.REMOTE_ACCESS:
        return config.tailnet_client(addr)
    return config.tailnet_client(addr) and addr.split("%")[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def _host_ok(host: str) -> bool:
    return host in LOCAL_HOSTS or (config.REMOTE_ACCESS and config.tailnet_host(host))


def _reply(status: HTTPStatus, body: bytes, ctype: str = "text/plain; charset=utf-8") -> Response:
    headers = Headers([("Content-Type", ctype), ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
                       ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer")])
    return Response(status.value, status.phrase, headers, body)


def _page() -> bytes:
    return PAGE.read_text(encoding="utf-8").replace("{name}", config.ROBOT_NAME).encode()


async def _process_request(connection, request):
    """Plain HTTP requests (the page) are answered here; a WebSocket upgrade on /ws falls through to the relay."""
    peer = connection.remote_address[0] if connection.remote_address else ""
    host = _hostname(request.headers.get("Host", ""))
    if not _client_ok(peer) or not _host_ok(host):
        return _reply(HTTPStatus.FORBIDDEN, b"forbidden\n")
    path = urlsplit(request.path).path
    if path == "/ws":
        origin = request.headers.get("Origin")
        if not origin or _hostname(urlsplit(origin).netloc) != host or \
                urlsplit(origin).netloc.lower() != (request.headers.get("Host") or "").strip().lower():
            return _reply(HTTPStatus.FORBIDDEN, b"forbidden\n")
        return None
    if path in ("/", "/index.html"):
        return _reply(HTTPStatus.OK, _page(), "text/html; charset=utf-8")
    return _reply(HTTPStatus.NOT_FOUND, b"not found\n")


async def _relay(browser) -> None:
    token = os.environ.get("ROBOT_TOKEN", "")
    try:
        async with websockets.connect(f"ws://127.0.0.1:{config.PORT}", max_size=1024 * 1024,
                                      open_timeout=5) as brain:
            await brain.send(json.dumps({"type": "hello", "who": "head", "fw": "web-1", "token": token}))

            async def up() -> None:
                first = True
                async for message in browser:
                    if first and isinstance(message, str):   # the page's own hello: the relay already said it
                        first = False
                        continue
                    first = False
                    await brain.send(message)

            async def down() -> None:
                async for message in brain:
                    await browser.send(message)

            tasks = [asyncio.create_task(up()), asyncio.create_task(down())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            for t in done:
                t.exception()   # collected so asyncio doesn't complain; the connection is closing anyway
    except (OSError, websockets.WebSocketException, asyncio.TimeoutError):
        pass
    finally:
        try:
            await browser.close()
        except Exception:
            pass


def _tls() -> ssl.SSLContext | None:
    cert, key = config.HEAD_TLS_CERT, config.HEAD_TLS_KEY
    if not cert or not key:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    return ctx


async def serve():
    """Start the head server on HEAD_PORT; returns the server (close it on shutdown). None if switched off."""
    if not config.HEAD_PORT:
        return None
    try:
        ctx = _tls()
    except (OSError, ssl.SSLError) as e:
        print(f"head: can't use the certificate ({e}); serving plain http (works on this computer only)")
        ctx = None
    try:
        server = await websockets.serve(_relay, "0.0.0.0", config.HEAD_PORT, ssl=ctx,
                                        process_request=_process_request, max_size=1024 * 1024)
    except OSError as e:
        print(f"head: port {config.HEAD_PORT} is busy ({e}); the web head is off")
        return None
    scheme = "https" if ctx else "http"
    where = "localhost" if not config.REMOTE_ACCESS else "this computer's address"
    print(f"web head: {scheme}://{where}:{config.HEAD_PORT}/  (open it on a phone or laptop and tap Wake)")
    if not ctx and config.REMOTE_ACCESS:
        print("  (no HEAD_TLS_CERT/HEAD_TLS_KEY: other devices can't use the microphone over plain http)")
    return server
