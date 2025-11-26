@echo off
REM Run Discovery Engine with custom duration

setlocal

set DURATION=%1
if "%DURATION%"=="" set DURATION=10

echo ============================================================
echo      AutoSecure Discovery Engine - Custom Duration
echo ============================================================
echo.
echo Scan duration: %DURATION% seconds
echo.

docker build -t autosecure-discovery-engine . >nul 2>&1

if errorlevel 1 (
    echo Error: Failed to build Docker image
    exit /b 1
)

REM Run with custom duration as environment variable
docker run -it --rm ^
    --name autosecure-discovery-engine ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -e SCAN_DURATION=%DURATION% ^
    autosecure-discovery-engine

echo.
echo Discovery complete!
