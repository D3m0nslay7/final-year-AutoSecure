@echo off
REM Run SSDP Generic Device in Docker
REM Usage: run-generic.bat [number_of_instances]
REM Example: run-generic.bat 3  (runs 3 instances)

setlocal enabledelayedexpansion

REM Default to 1 instance if no argument provided
set INSTANCES=%1
if "%INSTANCES%"=="" set INSTANCES=1

echo ============================================================
echo Building SSDP Generic Device Docker Image...
echo ============================================================
docker build -t autosecure-ssdp-generic .

echo.
echo ============================================================
echo Starting %INSTANCES% instance(s) of SSDP Generic Device
echo ============================================================
echo.

for /l %%i in (1,1,%INSTANCES%) do (
    set DEVICE_ID=!RANDOM!!RANDOM!
    echo [%%i/%INSTANCES%] Starting device with ID: !DEVICE_ID!
    docker run -d --name autosecure-ssdp-generic-%%i ^
        -e DEVICE_ID=!DEVICE_ID! ^
        autosecure-ssdp-generic
    timeout /t 1 /nobreak >nul
)

echo.
echo ============================================================
echo All devices started successfully!
echo ============================================================
echo.
echo To view logs: docker logs autosecure-ssdp-generic-1
echo To stop all: docker stop $(docker ps -q --filter name=autosecure-ssdp-generic)
echo To remove all: docker rm $(docker ps -aq --filter name=autosecure-ssdp-generic)
echo.
