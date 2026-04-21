@echo off
REM Complete AutoSecure Test - Devices + Main Engine Pipeline + Attacks
REM ============================================================
REM Runs the full AutoSecure pipeline:
REM   Discovery  - finds all IoT devices on the Docker bridge
REM   Segmentation - assigns devices to IOT / QUARANTINE segments
REM   Monitoring - sniffs for 60s and detects attacks
REM
REM ALSO launches the attack suite during the monitoring window
REM so the engine can detect and report every attack.
REM
REM Timeline:
REM   0s  - devices start
REM   5s  - engines container starts (discovery + segmentation + monitoring)
REM  30s  - attack container launches during monitoring window
REM  ~80s - monitoring finishes; full results printed
REM ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo         AutoSecure - Complete Testing Environment
echo ============================================================
echo.
echo This script will:
echo   1. Start all test devices in Docker containers
echo   2. Run the full engine pipeline (discovery + segmentation + monitoring)
echo   3. Fire all attack scripts during the monitoring window
echo   4. Display discovery, segmentation, and detection results
echo.
echo ============================================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

REM Ensure shared network exists (create silently if already present)
docker network create autosecure-net >nul 2>&1

echo [Step 1/4] Starting test devices...
echo.

cd Devices
call run-all-devices.bat

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start devices
    pause
    exit /b 1
)
cd ..

echo.
echo ============================================================
echo [Step 2/4] Waiting for devices to initialise (5s)...
echo ============================================================
echo.
timeout /t 5 /nobreak >nul

echo Devices are ready!
echo.

REM ── Build and start engines in background ─────────────────────────────────
echo ============================================================
echo [Step 3/4] Building and starting AutoSecure Engines (background)...
echo           Pipeline: Discovery + Segmentation + Monitoring (~80s total)
echo ============================================================
echo.

cd Engines
docker build -t autosecure-engines .
if errorlevel 1 (
    echo ERROR: Failed to build engines image
    cd ..
    pause
    exit /b 1
)

REM Start detached so we can launch attacks in parallel during monitoring
docker run -d ^
    --name autosecure-engines-run ^
    --network autosecure-net ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -v //var/run/docker.sock:/var/run/docker.sock ^
    autosecure-engines

if errorlevel 1 (
    echo ERROR: Failed to start engines container
    cd ..
    pause
    exit /b 1
)
cd ..

echo   Engines running in background [autosecure-engines-run]
echo   Waiting 30 seconds for discovery and segmentation to complete...
echo   Attacks will launch once the monitoring phase begins.
echo.
timeout /t 30 /nobreak >nul

REM ── Get container IPs and launch attacks ──────────────────────────────────
echo ============================================================
echo [Step 4/4] Launching attack suite against live devices...
echo ============================================================
echo.

for /f "tokens=*" %%i in ('docker inspect --format {{.NetworkSettings.IPAddress}} autosecure-mdns-generic-1 2^>nul') do set MDNS_GENERIC_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format {{.NetworkSettings.IPAddress}} autosecure-mdns-homekit-1 2^>nul') do set MDNS_HOMEKIT_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format {{.NetworkSettings.IPAddress}} autosecure-mqtt-mosquitto-1 2^>nul') do set MOSQUITTO_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format {{.NetworkSettings.IPAddress}} autosecure-mqtt-hivemq-1 2^>nul') do set HIVEMQ_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format {{.NetworkSettings.IPAddress}} autosecure-mqtt-emqx-1 2^>nul') do set EMQX_IP=%%i

echo   Target IPs:
echo     mDNS Generic  : %MDNS_GENERIC_IP%
echo     mDNS HomeKit  : %MDNS_HOMEKIT_IP%
echo     Mosquitto     : %MOSQUITTO_IP%
echo     HiveMQ        : %HIVEMQ_IP%
echo     EMQX          : %EMQX_IP%
echo.

REM Build attack runner image (attacks run inside Docker on same bridge)
docker build -t autosecure-attacks -f Attacks/Dockerfile.attacks Attacks/ >nul 2>&1

docker run --rm ^
    --name autosecure-attacks-run ^
    --network bridge ^
    -e MDNS_GENERIC_IP=%MDNS_GENERIC_IP% ^
    -e MDNS_HOMEKIT_IP=%MDNS_HOMEKIT_IP% ^
    -e MOSQUITTO_IP=%MOSQUITTO_IP% ^
    -e HIVEMQ_IP=%HIVEMQ_IP% ^
    -e EMQX_IP=%EMQX_IP% ^
    autosecure-attacks

echo.
echo ============================================================
echo   Attack suite finished. Waiting for monitoring to complete...
echo ============================================================
docker wait autosecure-engines-run >nul 2>&1

REM ── Print full results ────────────────────────────────────────────────────
echo.
echo ============================================================
echo   AUTOSECURE ENGINE OUTPUT
echo   (Discovery + Segmentation + Monitoring + Detected Attacks)
echo ============================================================
echo.
docker logs autosecure-engines-run 2>&1

docker rm autosecure-engines-run >nul 2>&1

echo.
echo ============================================================
echo                    Test Complete!
echo ============================================================
echo.
echo All devices are still running.
echo.
echo Options:
echo   - Run again:            run-complete-test.bat
echo   - Attacks only:         run-attack-test.bat
echo   - View device logs:     docker logs autosecure-mdns-generic-1
echo   - List all devices:     cd Devices ^&^& list-devices.bat
echo   - Stop all devices:     cd Devices ^&^& stop-all-devices.bat
echo.
echo ============================================================
echo.
pause
