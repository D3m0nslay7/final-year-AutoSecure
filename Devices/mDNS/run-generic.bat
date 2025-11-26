@echo off
REM Run mDNS Generic IoT Device in Docker
REM Usage: run-generic.bat [number_of_instances]
REM Example: run-generic.bat 3  (runs 3 instances)

setlocal enabledelayedexpansion

REM Default to 1 instance if no argument provided
set INSTANCES=%1
if "%INSTANCES%"=="" set INSTANCES=1

echo ============================================================
echo Building mDNS Generic IoT Device Docker Image...
echo ============================================================
docker build -t autosecure-mdns-generic .

echo.
echo ============================================================
echo Starting %INSTANCES% instance(s) of mDNS Generic IoT Device
echo ============================================================
echo.

for /l %%i in (1,1,%INSTANCES%) do (
    set DEVICE_ID=!RANDOM!!RANDOM!
    echo [%%i/%INSTANCES%] Starting device with ID: !DEVICE_ID!
    docker run -d --name autosecure-mdns-generic-%%i ^
        -e DEVICE_ID=!DEVICE_ID! ^
        autosecure-mdns-generic
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================================
echo All devices started successfully!
echo ============================================================
echo.
echo To view logs: docker logs autosecure-mdns-generic-1
echo To stop all: docker stop $(docker ps -q --filter name=autosecure-mdns-generic)
echo To remove all: docker rm $(docker ps -aq --filter name=autosecure-mdns-generic)
echo.
