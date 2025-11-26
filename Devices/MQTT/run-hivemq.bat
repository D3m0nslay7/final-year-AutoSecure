@echo off
REM Run MQTT HiveMQ Broker in Docker
REM Usage: run-hivemq.bat [number_of_instances]
REM Example: run-hivemq.bat 3  (runs 3 instances)

setlocal enabledelayedexpansion

REM Default to 1 instance if no argument provided
set INSTANCES=%1
if "%INSTANCES%"=="" set INSTANCES=1

echo ============================================================
echo Building MQTT HiveMQ Broker Docker Image...
echo ============================================================
docker build -t autosecure-mqtt-hivemq .

echo.
echo ============================================================
echo Starting %INSTANCES% instance(s) of MQTT HiveMQ Broker
echo ============================================================
echo.

for /l %%i in (1,1,%INSTANCES%) do (
    set /a MQTT_PORT=8883+%%i-1
    set /a WEB_PORT=8000+%%i-1
    echo [%%i/%INSTANCES%] Starting broker on ports !MQTT_PORT! (MQTT) and !WEB_PORT! (Web)
    docker run -d --name autosecure-mqtt-hivemq-%%i ^
        -p !MQTT_PORT!:8883 ^
        -p !WEB_PORT!:8000 ^
        autosecure-mqtt-hivemq python -u hivemq_broker.py
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================================
echo All brokers started successfully!
echo ============================================================
echo.
echo To view logs: docker logs autosecure-mqtt-hivemq-1
echo To stop all: docker stop $(docker ps -q --filter name=autosecure-mqtt-hivemq)
echo To remove all: docker rm $(docker ps -aq --filter name=autosecure-mqtt-hivemq)
echo.
