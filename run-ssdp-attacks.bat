@echo off
REM Run SSDP/UPnP attacks (multicast — no fixed target IP required)

setlocal enabledelayedexpansion

echo ============================================================
echo         AutoSecure - SSDP Attack Suite
echo ============================================================
echo.

REM Check Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    pause
    exit /b 1
)

REM Verify at least one SSDP device is running
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-ssdp-generic-1 2^>nul') do set SSDP_IP=%%i

if "%SSDP_IP%"=="" (
    echo ERROR: autosecure-ssdp-generic-1 is not running.
    echo Run: cd Devices ^&^& run-all-devices.bat
    pause
    exit /b 1
)

echo   SSDP device detected at: %SSDP_IP%
echo   (Attacks use multicast 239.255.255.250:1900 — no fixed IP needed)
echo.

echo Building attack image...
docker build -t autosecure-attacks -f Attacks/Dockerfile.attacks Attacks/ >nul 2>&1

echo.
echo [1/1] Running SSDP attack (M-SEARCH flood + fake NOTIFY + UPnP enum)...
docker run --rm --network autosecure-net ^
    --name autosecure-attack-ssdp ^
    autosecure-attacks ^
    python -u attack_ssdp.py --auto

echo.
echo ============================================================
echo   SSDP Attack Suite Complete
echo ============================================================
echo.
pause
