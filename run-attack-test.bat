@echo off
REM AutoSecure Attack Test
REM ============================================================
REM Starts all devices + monitoring engine, then fires all
REM attack scripts during the monitoring window and prints
REM what was detected.
REM
REM All containers share one named network: autosecure-net
REM This lets the engines container sniff all inter-container
REM traffic via Scapy in promiscuous mode on eth0.
REM
REM Timeline:
REM   0s   — network created, devices start
REM   5s   — engines container starts (discovery + segmentation + monitoring)
REM  60s   — attack container launches (monitoring window is now active)
REM  ~120s — monitoring finishes; results printed from engine logs
REM ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo      AutoSecure - Attack Detection Test
echo ============================================================
echo.
echo This script will:
echo   1. Start all test devices in Docker containers
echo   2. Run the full engine pipeline (discovery + segmentation + monitoring)
echo   3. Fire all attack scripts during the monitoring window
echo   4. Print which attacks were detected
echo.
echo ============================================================
echo.

REM ── Docker check ───────────────────────────────────────────────────────────
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

REM ── Cleanup: Remove any leftover containers and network from previous runs ──
echo [Cleanup] Removing any leftover AutoSecure containers and network...
docker rm -f autosecure-mdns-generic-1 autosecure-mdns-generic-2 >nul 2>&1
docker rm -f autosecure-mdns-homekit-1 autosecure-mdns-homekit-2 >nul 2>&1
docker rm -f autosecure-ssdp-generic-1 autosecure-ssdp-generic-2 >nul 2>&1
docker rm -f autosecure-mqtt-mosquitto-1 >nul 2>&1
docker rm -f autosecure-mqtt-hivemq-1 >nul 2>&1
docker rm -f autosecure-mqtt-emqx-1 >nul 2>&1
docker rm -f autosecure-engines-run >nul 2>&1
docker rm -f autosecure-attacks-run >nul 2>&1
docker network rm autosecure-net >nul 2>&1
echo   Done.
echo.

REM ── Create shared network ──────────────────────────────────────────────────
echo [Network] Creating shared Docker network: autosecure-net...
docker network create autosecure-net >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to create autosecure-net network
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Step 1: Start devices ──────────────────────────────────────────────────
echo [Step 1/5] Starting test devices on autosecure-net...
echo.
cd Devices
call run-all-devices.bat
if errorlevel 1 (
    echo ERROR: Failed to start devices
    pause
    exit /b 1
)
cd ..

echo.
echo ============================================================
echo [Step 2/5] Waiting for devices to initialise (5s)...
echo ============================================================
timeout /t 5 /nobreak >nul

REM ── Step 3: Build and start engines ───────────────────────────────────────
echo.
echo [Step 3/5] Building and starting the AutoSecure engines (background)...
echo           Discovery + Segmentation + Monitoring will run for ~80 seconds.
echo.

cd Engines
docker build -t autosecure-engines . >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to build engines image
    cd ..
    pause
    exit /b 1
)

REM Start engines in DETACHED mode so we can run attacks in parallel
REM Note: no --rm so the container persists after exit for log retrieval
docker run -d ^
    --name autosecure-engines-run ^
    --network autosecure-net ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    autosecure-engines

if errorlevel 1 (
    echo ERROR: Failed to start engines container
    cd ..
    pause
    exit /b 1
)
cd ..

echo   Engines running in background (container: autosecure-engines-run)
echo.

REM ── Step 4: Wait for discovery + segmentation to complete ─────────────────
REM Discovery alone takes ~25-30s (mDNS 10s + SSDP 10s + MQTT scan 5s+).
REM We wait 60s to ensure discovery + segmentation are done and monitoring
REM has started its 60s sniff window before attacks fire.
echo ============================================================
echo [Step 4/5] Waiting 60s for discovery and segmentation to complete...
echo           Attacks will launch once monitoring phase begins.
echo ============================================================
timeout /t 60 /nobreak >nul

REM ── Step 5: Get container IPs and launch attacks ───────────────────────────
echo.
echo [Step 5/5] Launching attack suite against live devices...
echo.

REM Collect container IPs (now on autosecure-net, not default bridge)
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mdns-generic-1 2^>nul') do set MDNS_GENERIC_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mdns-homekit-1 2^>nul') do set MDNS_HOMEKIT_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-mosquitto-1 2^>nul') do set MOSQUITTO_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-hivemq-1 2^>nul') do set HIVEMQ_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-emqx-1 2^>nul') do set EMQX_IP=%%i

echo   Container IPs discovered:
echo     mDNS Generic  : %MDNS_GENERIC_IP%
echo     mDNS HomeKit  : %MDNS_HOMEKIT_IP%
echo     Mosquitto     : %MOSQUITTO_IP%
echo     HiveMQ        : %HIVEMQ_IP%
echo     EMQX          : %EMQX_IP%
echo.

REM Build attack runner image
echo   Building attack runner image...
docker build -t autosecure-attacks -f Attacks/Dockerfile.attacks Attacks/ >nul 2>&1

REM Run attacks on the same autosecure-net network
docker run --rm ^
    --name autosecure-attacks-run ^
    --network autosecure-net ^
    --cap-add=NET_RAW ^
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
echo.

REM Wait for the engines container to finish
docker wait autosecure-engines-run >nul 2>&1

REM ── Print monitoring results ───────────────────────────────────────────────
echo.
echo ============================================================
echo   MONITORING ENGINE RESULTS
echo   (What was detected during the attack window)
echo ============================================================
echo.
docker logs autosecure-engines-run 2>&1

REM Clean up
docker rm autosecure-engines-run >nul 2>&1

echo.
echo ============================================================
echo                   Test Complete!
echo ============================================================
echo.
echo Devices are still running on autosecure-net.
echo   Stop all: cd Devices ^&^& stop-all-devices.bat
echo.
pause
