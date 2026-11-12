# Security policy

## Supported versions

The latest release receives security fixes.

## Reporting a vulnerability

Please do not publish the details of a vulnerability in a public issue. Use the
"Report a vulnerability" button of the repository's Security tab (GitHub private
vulnerability reporting) if it is available; otherwise open an issue that asks
for a private contact and contains no details of the problem.

## What to know before exposing ONE-PIX

The web interface controls hardware (projector, spectrometer, camera) and files.

- **It has no sign-in.** Anyone who can reach its port can start an acquisition,
  change the configuration, read and delete measurements and install plugins.
  It listens on all interfaces: use it on a network you trust (a private
  network, a VPN such as Tailscale) and not on the open internet.
- It does not use HTTPS. On a network you do not trust, use an SSH tunnel or a
  reverse proxy with TLS.
- A web page of another site cannot make your browser act on it: requests that
  change something and that the browser reports as cross-site are refused
  (`app/GUI/flask/request_guard.py`). A page whose name is made to resolve to
  this machine (DNS rebinding) is not stopped by this.
- Uploads are limited to 1024 MB (`ONEPIX_MAX_UPLOAD_MB` changes it).
- The Socket.IO server (`app/websocket_server`) refuses connections without
  `ONEPIX_WS_TOKEN`. It listens on all interfaces.
- Flask's debugger (`FLASK_DEBUG=1`) must never be enabled on a shared network.
- Plugins are Python packages that run with the application's rights: install
  only the ones you trust.
