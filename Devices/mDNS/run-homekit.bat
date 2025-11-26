@echo off
REM Run mDNS HomeKit Device in Docker
REM Usage: run-homekit.bat [number_of_instances]
REM Example: run-homekit.bat 3  (runs 3 instances)

setlocal enabledelayedexpansion

REM Default to 1 instance if no argument provided
set INSTANCES=%1
if "%INSTANCES%"=="" set INSTANCES=1

echo ============================================================
echo Building mDNS HomeKit Device Docker Image...
echo ============================================================
docker build -t autosecure-mdns-homekit .

echo.
echo ============================================================
echo Starting %INSTANCES% instance(s) of mDNS HomeKit Device
echo ============================================================
echo.

for /l %%i in (1,1,%INSTANCES%) do (
    set DEVICE_ID=!RANDOM!!RANDOM!
    echo [%%i/%INSTANCES%] Starting device with ID: !DEVICE_ID!
    docker run -d --name autosecure-mdns-homekit-%%i ^
        -e DEVICE_ID=!DEVICE_ID! ^
        autosecure-mdns-homekit python -u homekit_device.py
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================================
echo All devices started successfully!
echo ============================================================
echo.
echo To view logs: docker logs autosecure-mdns-homekit-1
echo To stop all: docker stop $(docker ps -q --filter name=autosecure-mdns-homekit)
echo To remove all: docker rm $(docker ps -aq --filter name=autosecure-mdns-homekit)
echo.
