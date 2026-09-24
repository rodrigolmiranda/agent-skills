# Central delivery dashboard

One always-served page for every project under the shared coordination root
(`<root>/projects/<project>/continuation.json`). A project appears as soon as its coordinator writes that record
when the plan starts; nothing has to register it. Pages render per request; there is no background refresh.
The server is read-only, binds to loopback, and shows only sanitized facts (state, tool-call count, last output
time), never raw worker output.

Pick one:

| Option | Survives reboot | Command |
|---|---|---|
| Docker (default) | yes, if Docker starts at login | `INTERCHANGE_ROOT=<root> docker compose up -d` in this folder |
| macOS launchd (no Docker) | yes | fill `interchange.dashboard.plist.template`, then `launchctl load ...` |
| Foreground | no | `python3 skills/interchange/scripts/dashboard_server.py --root <root>` |
| None | — | the coordinator gives a `file://` link to the per-repository board instead |

Default URL: `http://127.0.0.1:7390/`. A coordinator checks the URL answers before giving it to the owner, and
falls back to the `file://` board when it doesn't.
