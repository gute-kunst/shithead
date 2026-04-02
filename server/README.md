[![Test Shithead Server](https://github.com/gute-kunst/shithead_browsergame/actions/workflows/server.yml/badge.svg)](https://github.com/gute-kunst/shithead_browsergame/actions/workflows/server.yml)
# pyshithead
## Start Server
```uvicorn pyshithead.main:app```

Persistent session state is now stored in SQLite by default so active tables can survive a short restart.

Optional configuration:
- `DATABASE_URL`
  - default: `sqlite:///./shithead.db`
  - currently only `sqlite:///...` URLs are supported

## Development
### Getting Started
#### Start Development Server

```uvicorn pyshithead.main:app --reload```

#### Start Debug Preset Server

```poetry run python -m pyshithead.debug_server --preset choose-public```

Available presets:
- `lobby-2p`
- `choose-public`
- `normal-turn`
- `host-specials`
- `host-specials-lock`
- `hidden-reveal`
- `hidden-take`
- `revealed-joker`
- `revealed-seven`
- `game-over`

#### Prompt Toolkit error
in the following file: ```~AppData\Local\pypoetry\Cache\virtualenvs\shithead-server-env\Lib\site-packages\prompt_toolkit\styles\from_dict.py```
replace the import of collections ```from collections import Mapping``` with the following line ```from collections.abc import Mapping```.

https://jacobian.org/til/github-actions-poetry/
