@echo off
REM Run all AutoSecure attack suites: MQTT + SSDP + ARP

setlocal enabledelayedexpansion

echo ============================================================
echo         AutoSecure - Full Attack Suite
echo ============================================================
echo.

REM Check Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    pause
    exit /b 1
)

REM Verify devices are up before proceeding
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mdns-generic-1 2^>nul') do set MDNS_GENERIC_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mdns-homekit-1 2^>nul') do set MDNS_HOMEKIT_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-ssdp-generic-1 2^>nul') do set SSDP_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-mosquitto-1 2^>nul') do set MOSQUITTO_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-hivemq-1 2^>nul') do set HIVEMQ_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-emqx-1 2^>nul') do set EMQX_IP=%%i

if "%MOSQUITTO_IP%"=="" (
    echo ERROR: Devices are not running. Start them first:
    echo   cd Devices ^&^& run-all-devices.bat
    pause
    exit /b 1
)

REM Get network gateway for ARP victim
for /f "tokens=*" %%i in ('docker network inspect autosecure-net --format "{{range .IPAM.Config}}{{.Gateway}}{{end}}" 2^>nul') do set VICTIM_IP=%%i
if "%VICTIM_IP%"=="" set VICTIM_IP=172.17.0.1

echo   Target IPs:
echo     mDNS Generic  : %MDNS_GENERIC_IP%
echo     mDNS HomeKit  : %MDNS_HOMEKIT_IP%
echo     SSDP          : %SSDP_IP%
echo     Mosquitto     : %MOSQUITTO_IP%
echo     HiveMQ        : %HIVEMQ_IP%
echo     EMQX          : %EMQX_IP%
echo     ARP victim    : %VICTIM_IP%
echo.

echo Building attack images...
docker build -t autosecure-attacks -f Attacks/Dockerfile.attacks Attacks/ >nul 2>&1
docker build -t autosecure-arp-attack -f Attacks/Dockerfile.arp_spoof Attacks/ >nul 2>&1

echo.
echo ============================================================
echo [1/5] Generic IoT attack...
echo ============================================================
docker run --rm --network autosecure-net ^
    --name autosecure-attack-generic ^
    autosecure-attacks ^
    python -u attack_generic_iot.py %MDNS_GENERIC_IP% 80 --auto

echo.
echo ============================================================
echo [2/5] MQTT attacks (Mosquitto + HiveMQ + EMQX)...
echo ============================================================
docker run --rm --network autosecure-net ^
    --name autosecure-attack-mosquitto ^
    autosecure-attacks ^
    python -u attack_mosquitto.py %MOSQUITTO_IP% 1883 --auto

docker run --rm --network autosecure-net ^
    --name autosecure-attack-hivemq ^
    autosecure-attacks ^
    python -u attack_hivemq.py %HIVEMQ_IP% 8883 8000 --auto

docker run --rm --network autosecure-net ^
    --name autosecure-attack-emqx ^
    autosecure-attacks ^
    python -u attack_emqx.py %EMQX_IP% 8884 18083 --auto

echo.
echo ============================================================
echo [3/5] SSDP attack...
echo ============================================================
docker run --rm --network autosecure-net ^
    --name autosecure-attack-ssdp ^
    autosecure-attacks ^
    python -u attack_ssdp.py --auto

echo.
echo ============================================================
echo [4/5] HomeKit attack...
echo ============================================================
docker run --rm --network autosecure-net ^
    --name autosecure-attack-homekit ^
    autosecure-attacks ^
    python -u attack_homekit.py %MDNS_HOMEKIT_IP% 8080 --auto

echo.
echo ============================================================
echo [5/5] ARP spoof attack...
echo ============================================================
docker run --rm ^
    --name autosecure-attack-arp ^
    --network autosecure-net ^
    --cap-add=NET_RAW ^
    --cap-add=NET_ADMIN ^
    autosecure-arp-attack ^
    %MDNS_GENERIC_IP% %VICTIM_IP%

echo.
echo ============================================================
echo   Full Attack Suite Complete
echo ============================================================
echo.
pause
