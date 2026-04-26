@echo off
REM Run MQTT attacks against Mosquitto, HiveMQ, and EMQX containers

setlocal enabledelayedexpansion

echo ============================================================
echo         AutoSecure - MQTT Attack Suite
echo ============================================================
echo.

REM Check Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    pause
    exit /b 1
)

REM Get container IPs
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-mosquitto-1 2^>nul') do set MOSQUITTO_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-hivemq-1 2^>nul') do set HIVEMQ_IP=%%i
for /f "tokens=*" %%i in ('docker inspect --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" autosecure-mqtt-emqx-1 2^>nul') do set EMQX_IP=%%i

if "%MOSQUITTO_IP%"=="" (
    echo ERROR: autosecure-mqtt-mosquitto-1 is not running.
    echo Run: cd Devices ^&^& run-all-devices.bat
    pause
    exit /b 1
)

echo   Target IPs:
echo     Mosquitto : %MOSQUITTO_IP%
echo     HiveMQ    : %HIVEMQ_IP%
echo     EMQX      : %EMQX_IP%
echo.

echo Building attack image...
docker build -t autosecure-attacks -f Attacks/Dockerfile.attacks Attacks/ >nul 2>&1

echo.
echo [1/3] Running Mosquitto attack (port 1883)...
docker run --rm --network autosecure-net ^
    --name autosecure-attack-mosquitto ^
    autosecure-attacks ^
    python -u attack_mosquitto.py %MOSQUITTO_IP% 1883 --auto

echo.
echo [2/3] Running HiveMQ attack (port 8883 / web 8000)...
docker run --rm --network autosecure-net ^
    --name autosecure-attack-hivemq ^
    autosecure-attacks ^
    python -u attack_hivemq.py %HIVEMQ_IP% 8883 8000 --auto

echo.
echo [3/3] Running EMQX attack (port 8884 / dashboard 18083)...
docker run --rm --network autosecure-net ^
    --name autosecure-attack-emqx ^
    autosecure-attacks ^
    python -u attack_emqx.py %EMQX_IP% 8884 18083 --auto

echo.
echo ============================================================
echo   MQTT Attack Suite Complete
echo ============================================================
echo.
pause
