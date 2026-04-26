@echo off
REM Run AutoSecure Engines continuously - loops discovery + segmentation + monitoring

setlocal enabledelayedexpansion

echo ============================================================
echo         AutoSecure Engines - Continuous Monitor
echo ============================================================
echo.
echo Engines will run in a loop. Each cycle:
echo   1. Discovery     - scans for IoT devices
echo   2. Segmentation  - assigns devices to network segments
echo   3. Monitoring    - sniffs traffic and detects attacks (~60s)
echo.
echo Press Ctrl+C to stop.
echo ============================================================
echo.

REM Check Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    pause
    exit /b 1
)

REM Check autosecure-net exists
docker network inspect autosecure-net >nul 2>&1
if errorlevel 1 (
    echo ERROR: autosecure-net network not found.
    echo Run: cd Devices ^&^& run-all-devices.bat
    pause
    exit /b 1
)

echo Building AutoSecure Engines Docker image...
docker build -t autosecure-engines .
if errorlevel 1 (
    echo ERROR: Failed to build Docker image
    pause
    exit /b 1
)

echo.
echo Build complete. Starting monitoring loop...
echo.

set CYCLE=1

:loop
echo ============================================================
echo   CYCLE %CYCLE% — Starting at %DATE% %TIME%
echo ============================================================
echo.

REM Remove any leftover container from previous cycle
docker rm -f autosecure-engines >nul 2>&1

REM Start engine detached (no --rm so logs persist until we read them)
REM Docker socket is mounted so the engine can run `docker exec` into device containers for tcpdump
docker run -d ^
    --name autosecure-engines ^
    --network autosecure-net ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -v //var/run/docker.sock:/var/run/docker.sock ^
    autosecure-engines >nul

if errorlevel 1 (
    echo ERROR: Failed to start engines container
    pause
    exit /b 1
)

REM Stream logs live until the container exits
docker logs -f autosecure-engines 2>&1

REM Container has exited - print separator then loop
echo.
echo ============================================================
echo   CYCLE %CYCLE% COMPLETE — %DATE% %TIME%
echo   Restarting in 5 seconds... (Ctrl+C to stop)
echo ============================================================
echo.

REM Clean up the finished container before next cycle
docker rm autosecure-engines >nul 2>&1

set /a CYCLE+=1
timeout /t 5 /nobreak >nul
goto loop
