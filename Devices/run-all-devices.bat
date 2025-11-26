@echo off
REM Master script to run all AutoSecure test devices in Docker
REM Each device type can be customized with number of instances

setlocal enabledelayedexpansion

echo ============================================================
echo        AutoSecure Test Devices - Docker Launcher
echo ============================================================
echo.
echo This script will start all test devices in Docker containers.
echo Each device type runs in separate containers with unique IPs.
echo.
echo Default configuration:
echo   - 2x mDNS Generic IoT Devices
echo   - 2x mDNS HomeKit Devices
echo   - 2x SSDP Generic Devices
echo   - 1x MQTT Mosquitto Broker
echo   - 1x MQTT HiveMQ Broker
echo   - 1x MQTT EMQX Broker
echo.
echo ============================================================
echo.

REM Build all images first
echo [1/4] Building Docker images...
echo.

cd mDNS
echo   Building mDNS images...
docker build -t autosecure-mdns-generic . >nul 2>&1
docker build -t autosecure-mdns-homekit . >nul 2>&1

cd ..\SSDP
echo   Building SSDP images...
docker build -t autosecure-ssdp-generic . >nul 2>&1

cd ..\MQTT
echo   Building MQTT images...
docker build -t autosecure-mqtt-mosquitto . >nul 2>&1
docker build -t autosecure-mqtt-hivemq . >nul 2>&1
docker build -t autosecure-mqtt-emqx . >nul 2>&1

cd ..

echo.
echo [2/4] Starting mDNS devices...
echo.

REM Start mDNS Generic devices
for /l %%i in (1,1,2) do (
    set DEVICE_ID=!RANDOM!!RANDOM!
    echo   [%%i/2] Starting mDNS Generic IoT Device !DEVICE_ID!
    docker run -d --name autosecure-mdns-generic-%%i ^
        -e DEVICE_ID=!DEVICE_ID! ^
        autosecure-mdns-generic >nul
    timeout /t 1 /nobreak >nul
)

REM Start mDNS HomeKit devices
for /l %%i in (1,1,2) do (
    set DEVICE_ID=!RANDOM!!RANDOM!
    echo   [%%i/2] Starting mDNS HomeKit Device !DEVICE_ID!
    docker run -d --name autosecure-mdns-homekit-%%i ^
        -e DEVICE_ID=!DEVICE_ID! ^
        autosecure-mdns-homekit python -u homekit_device.py >nul
    timeout /t 1 /nobreak >nul
)

echo.
echo [3/4] Starting SSDP devices...
echo.

REM Start SSDP devices
for /l %%i in (1,1,2) do (
    set DEVICE_ID=!RANDOM!!RANDOM!
    echo   [%%i/2] Starting SSDP Generic Device !DEVICE_ID!
    docker run -d --name autosecure-ssdp-generic-%%i ^
        -e DEVICE_ID=!DEVICE_ID! ^
        autosecure-ssdp-generic >nul
    timeout /t 1 /nobreak >nul
)

echo.
echo [4/4] Starting MQTT brokers...
echo.

REM Start MQTT Mosquitto
echo   [1/3] Starting MQTT Mosquitto Broker (port 1883)
docker run -d --name autosecure-mqtt-mosquitto-1 ^
    -p 1883:1883 ^
    autosecure-mqtt-mosquitto >nul
timeout /t 1 /nobreak >nul

REM Start MQTT HiveMQ
echo   [2/3] Starting MQTT HiveMQ Broker (port 8883)
docker run -d --name autosecure-mqtt-hivemq-1 ^
    -p 8883:8883 -p 8000:8000 ^
    autosecure-mqtt-hivemq python -u hivemq_broker.py >nul
timeout /t 1 /nobreak >nul

REM Start MQTT EMQX
echo   [3/3] Starting MQTT EMQX Broker (port 8884)
docker run -d --name autosecure-mqtt-emqx-1 ^
    -p 8884:8884 -p 18083:18083 ^
    autosecure-mqtt-emqx python -u emqx_broker.py >nul
timeout /t 1 /nobreak >nul

echo.
echo ============================================================
echo                 ALL DEVICES STARTED!
echo ============================================================
echo.
echo Running containers:
docker ps --filter name=autosecure- --format "  - {{.Names}} ({{.Status}})"
echo.
echo ============================================================
echo.
echo Useful commands:
echo   View logs:        docker logs autosecure-mdns-generic-1
echo   List containers:  docker ps --filter name=autosecure-
echo   Stop all devices: stop-all-devices.bat
echo.
echo ============================================================
echo.
