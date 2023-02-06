[![Test Shithead Server](https://github.com/gute-kunst/shithead_browsergame/actions/workflows/server.yml/badge.svg)](https://github.com/gute-kunst/shithead_browsergame/actions/workflows/server.yml)
# pyshithead
## Start Server
```uvicorn pyshithead.main:app --reload```
## Development
### Getting Started
in the following file: ```~AppData\Local\pypoetry\Cache\virtualenvs\shithead-server-env\Lib\site-packages\prompt_toolkit\styles\from_dict.py```
replace the import of collections ```from collections import Mapping``` with the following line ```from collections.abc import Mapping```.

https://jacobian.org/til/github-actions-poetry/
