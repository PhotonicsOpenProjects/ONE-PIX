# Security policy

## Supported versions

The latest release receives security fixes.

## Reporting a vulnerability

Please do not publish details of a vulnerability in a public issue. Use the
"Report a vulnerability" button of the repository's Security tab (GitHub private
vulnerability reporting) if it is available; otherwise open an issue that asks
for a private contact and contains no exploit details.

## What to know before exposing ONE-PIX

The web interface controls hardware (projector, spectrometer, camera) and files.

- It listens on `127.0.0.1` by default. `ONEPIX_HOST` opens it to a network and
  then requires `ONEPIX_WEB_TOKEN`; the server refuses to start otherwise.
- It does not use HTTPS. On an untrusted network, use an SSH tunnel or a
  reverse proxy with TLS.
- The Socket.IO server (`app/websocket_server`) refuses connections without
  `ONEPIX_WS_TOKEN`. It listens on all interfaces: keep it on a trusted network.
- Flask's debugger (`FLASK_DEBUG=1`) must never be enabled on a shared network.
- Plugins are Python packages that run with the application's rights: install
  only the ones you trust.

See "Network access and security" in the README for the variables.
