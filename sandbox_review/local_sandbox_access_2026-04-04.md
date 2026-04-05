# Local Sandbox Access Review

## What changed

- Added HTTP-based sandbox discovery alongside the older raw message probe path.
- Pointed the local project `.env` at the running local Core Engine sandbox on `127.0.0.1:800`.
- Updated `health-check` and `discover-api` so they now report live sandbox surfaces, not just host/port config.
- Extended the read-only local install inspection so it now exposes install-backed session/layer state:
  - parsed `.iceLayer` layer exports
  - parsed `.ivwts` browser tabsets
  - parsed Open Stage Control session data
- Extended the read-only local discovery again so it now scans configured user session-library roots for saved `.iceSession` files.

## What was verified

- The local sandbox is reachable through the Core Engine control panel surface on `http://127.0.0.1:800/`.
- The read-only sources endpoint is reachable at `http://127.0.0.1:800/api/sources/ignoreList`.
- Socket.IO handshaking is available at `http://127.0.0.1:800/socket.io/?EIO=4&transport=polling`.
- Related Streetview sidecar surfaces are reachable on port `9070`.
- A read-only live source snapshot can now be collected through Socket.IO after `ics-ready`.
- The current sandbox state reports `0` exposed capture sources, which is now surfaced explicitly instead of being treated as a probe failure.
- The nearby install was detected read-only at `C:\igloo\igloo-core-service`.
- Read-only install-backed layer/session state is now visible:
  - `1` parsed layer export: `Clickshare` of type `NDI`
  - `4` parsed browser tabsets, including `Google Earth`, `Matterport`, `Streetview`, and `ThingLink`
  - Open Stage Control session with `10` widgets, `3` panels, `6` buttons, and targets on `localhost:9016`, `9040`, and `9041`
- Read-only saved-session state is now visible from `C:\Users\AshtonKehinde\OneDrive - igloovision\Desktop`:
  - `MakVideos.iceSession`: immersive 360 playback session, not exported with assets, one `Traffic.mp4` layer, triggers/actions enabled
  - `Quiddiya.iceSession`: immersive 360 playback session, exported with assets, one `Quiddiya_mmck_5.1.mov` layer, adjacent `Assets` folder present
- The configured content folder path `C:\igloo\content` does not currently exist, and that is now treated as an expected clean-sandbox baseline rather than a failure.
- CLI verification passed:
  - `python -m unittest discover -s tests -v`
  - `python -m compileall src`
  - `python -m igloo_experience_builder health-check`
  - `python -m igloo_experience_builder discover-api`

## What assumptions remain

- This is still discovery-only and read-only.
- The refreshed live review files were generated through the installed Windows Python interpreter, and that interpreter does not currently have optional packages like `python-socketio` or `pypdf`.
- Because of that interpreter mismatch, the latest JSON refresh shows `sandbox_live_state = dependency_missing` even though we had already validated the Socket.IO source snapshot earlier.
- No write-capable commands have been attempted.
- The most useful session/layer picture currently comes from install-backed artifacts rather than a richer runtime session API feed.
- Sandbox success still means technically reproducible in this local environment, not ready to promise to a client.

## Next recommended step

- Keep `127.0.0.1:800` as the primary local sandbox entry point for Phase 2 review.
- Use the install-backed layer, tabset, Open Stage Control, and saved-session library state as the current read-only review baseline.
- If you expect richer live runtime state, the next best check is whether the sandbox simply has no active capture sources configured yet, rather than a connectivity problem in the agent.
- The next safe extension would be using these real `.iceSession` patterns to drive a direct session-folder/package writer before any write-back into the sandbox install is considered.
