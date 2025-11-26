@echo off
REM Run MQTT EMQX Broker in Docker
REM Usage: run-emqx.bat [number_of_instances]
REM Example: run-emqx.bat 3  (runs 3 instances)

setlocal enabledelayedexpansion

REM Default to 1 instance if no argument provided
set INSTANCES=%1
if "%INSTANCES%"=="" set INSTANCES=1

echo ============================================================
echo Building MQTT EMQX Broker Docker Image...
echo ============================================================
docker build -t autosecure-mqtt-emqx .

echo.
echo ============================================================
echo Starting %INSTANCES% instance(s) of MQTT EMQX Broker
echo ============================================================
echo.

for /l %%i in (1,1,%INSTANCES%) do (
    set /a MQTT_PORT=8884+%%i-1
    set /a DASHBOARD_PORT=18083+%%i-1
    echo [%%i/%INSTANCES%] Starting broker on ports !MQTT_PORT! (MQTT) and !DASHBOARD_PORT! (Dashboard)
    docker run -d --name autosecure-mqtt-emqx-%%i ^
        -p !MQTT_PORT!:8884 ^
        -p !DASHBOARD_PORT!:18083 ^
        autosecure-mqtt-emqx python -u emqx_broker.py
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================================
echo All brokers started successfully!
echo ============================================================
echo.
echo To view logs: docker logs autosecure-mqtt-emqx-1
echo To stop all: docker stop $(docker ps -q --filter name=autosecure-mqtt-emqx)
echo To remove all: docker rm $(docker ps -aq --filter name=autosecure-mqtt-emqx)
echo.
