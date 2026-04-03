[![Test Shithead Server](https://github.com/gute-kunst/shithead_browsergame/actions/workflows/server.yml/badge.svg)](https://github.com/gute-kunst/shithead_browsergame/actions/workflows/server.yml)
# pyshithead

Canonical project docs:

- architecture: `../docs/architecture.md`
- development commands: `../docs/dev.md`
- work tracking: `../work/INDEX.md`

## Start Server
```uvicorn pyshithead.main:app```

Persistent session state is now stored in SQLite by default so active tables can survive a short restart.

Disconnect handling is mobile-friendly by default:
- players are marked offline as soon as their WebSocket drops
- lobby seats stay reserved until the host removes the offline player
- setup-phase seats auto-remove only after 10 minutes
- an offline active turn auto-resolves only after 5 minutes
- the host can remove offline non-host players through the browser UI or `POST /api/games/{invite_code}/players/{seat}/kick`

Optional configuration:
- `DATABASE_URL`
  - default: `sqlite:///./shithead.db`
  - currently only `sqlite:///...` URLs are supported

## Development
### Getting Started
#### Start Development Server

```uvicorn pyshithead.main:app --reload```

#### Install Dependencies And Browser Runtime

```powershell
poetry install
poetry run python -m playwright install chromium
```

#### Canonical Verification

```powershell
poetry run python -m pytest tests/test_alpha_api.py -q
poetry run python -m pytest tests_browser/test_debug_presets.py tests_browser/test_browser_smoke.py -q -o addopts=''
```

#### Start Debug Preset Server

```poetry run python -m pyshithead.debug_server --preset choose-public```

Available presets:
- `lobby-2p`
- `choose-public`
- `normal-turn`
- `host-specials`
- `host-specials-lock`
- `host-turn-15`
- `hidden-reveal`
- `hidden-take`
- `revealed-joker`
- `revealed-seven`
- `game-over`

#### Prompt Toolkit error
in the following file: ```~AppData\Local\pypoetry\Cache\virtualenvs\shithead-server-env\Lib\site-packages\prompt_toolkit\styles\from_dict.py```
replace the import of collections ```from collections import Mapping``` with the following line ```from collections.abc import Mapping```.

https://jacobian.org/til/github-actions-poetry/
