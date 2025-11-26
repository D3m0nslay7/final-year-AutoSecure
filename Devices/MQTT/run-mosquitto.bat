@echo off
REM Run MQTT Mosquitto Broker in Docker
REM Usage: run-mosquitto.bat [number_of_instances]
REM Example: run-mosquitto.bat 3  (runs 3 instances)

setlocal enabledelayedexpansion

REM Default to 1 instance if no argument provided
set INSTANCES=%1
if "%INSTANCES%"=="" set INSTANCES=1

echo ============================================================
echo Building MQTT Mosquitto Broker Docker Image...
echo ============================================================
docker build -t autosecure-mqtt-mosquitto .

echo.
echo ============================================================
echo Starting %INSTANCES% instance(s) of MQTT Mosquitto Broker
echo ============================================================
echo.

for /l %%i in (1,1,%INSTANCES%) do (
    set /a PORT=1883+%%i-1
    echo [%%i/%INSTANCES%] Starting broker on port !PORT!
    docker run -d --name autosecure-mqtt-mosquitto-%%i ^
        -p !PORT!:1883 ^
        autosecure-mqtt-mosquitto
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================================
echo All brokers started successfully!
echo ============================================================
echo.
echo To view logs: docker logs autosecure-mqtt-mosquitto-1
echo To stop all: docker stop $(docker ps -q --filter name=autosecure-mqtt-mosquitto)
echo To remove all: docker rm $(docker ps -aq --filter name=autosecure-mqtt-mosquitto)
echo.
