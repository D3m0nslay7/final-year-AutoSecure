@echo off
REM Run ARP spoofing attack — targets the first mDNS device with the gateway as victim

setlocal enabledelayedexpansion

echo ============================================================
echo         AutoSecure - ARP Spoof Attack
echo ============================================================
echo.

REM Check Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    pause
    exit /b 1
)

REM Use first mDNS device as target and gateway (172.17.0.1) as victim
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mdns-generic-1 2^>nul') do set TARGET_IP=%%i

if "%TARGET_IP%"=="" (
    echo ERROR: autosecure-mdns-generic-1 is not running.
    echo Run: cd Devices ^&^& run-all-devices.bat
    pause
    exit /b 1
)

REM Victim is the network gateway of autosecure-net
for /f "tokens=*" %%i in ('docker network inspect autosecure-net --format "{{range .IPAM.Config}}{{.Gateway}}{{end}}" 2^>nul') do set VICTIM_IP=%%i

if "%VICTIM_IP%"=="" (
    REM Fall back to default bridge gateway
    set VICTIM_IP=172.17.0.1
)

echo   Target (spoofed) : %TARGET_IP%
echo   Victim (poisoned): %VICTIM_IP%
echo.

echo Building ARP spoof image...
docker build -t autosecure-arp-attack -f Attacks/Dockerfile.arp_spoof Attacks/ >nul 2>&1

echo.
echo [1/1] Running ARP spoof attack (broadcast + cache poison + ARP recon)...
docker run --rm ^
    --name autosecure-attack-arp ^
    --network autosecure-net ^
    --cap-add=NET_RAW ^
    --cap-add=NET_ADMIN ^
    autosecure-arp-attack ^
    %TARGET_IP% %VICTIM_IP%

echo.
echo ============================================================
echo   ARP Attack Suite Complete
echo ============================================================
echo.
pause
