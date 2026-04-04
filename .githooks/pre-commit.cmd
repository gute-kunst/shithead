@echo off
setlocal

for /f "delims=" %%I in ('git rev-parse --show-toplevel') do set "REPO_ROOT=%%I"
cd /d "%REPO_ROOT%\server" || exit /b 1

poetry run python -m black --check pyshithead/main.py pyshithead/models/common/game_manager.py pyshithead/models/game/game.py pyshithead/models/session/manager.py tests/test_alpha_api.py tests_browser
if errorlevel 1 exit /b 1

poetry run python -m isort --check-only pyshithead/main.py pyshithead/models/common/game_manager.py pyshithead/models/game/game.py pyshithead/models/session/manager.py tests/test_alpha_api.py tests_browser
