@echo off
setlocal

for /f "delims=" %%I in ('git rev-parse --show-toplevel') do set "REPO_ROOT=%%I"
cd /d "%REPO_ROOT%"

git config --local core.hooksPath .githooks
echo Configured core.hooksPath=.githooks
