@echo off
REM Stop and remove all AutoSecure test device containers

echo ============================================================
echo   Stopping All AutoSecure Test Device Containers
echo ============================================================
echo.

REM Stop all running containers
echo Stopping containers...
for /f "tokens=*" %%i in ('docker ps -q --filter name=autosecure-') do (
    docker stop %%i >nul 2>&1
)

echo.
echo Removing containers...
for /f "tokens=*" %%i in ('docker ps -aq --filter name=autosecure-') do (
    docker rm %%i >nul 2>&1
)

echo.
echo ============================================================
echo            All AutoSecure Devices Stopped
echo ============================================================
echo.
echo Remaining containers:
docker ps --filter name=autosecure- --format "  - {{.Names}}" 2>nul
if errorlevel 1 echo   (None)
echo.
