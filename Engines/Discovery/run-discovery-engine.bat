@echo off
REM Run Discovery Engine in Docker on the same network as test devices

echo ============================================================
echo      AutoSecure Discovery Engine - Docker Launcher
echo ============================================================
echo.
echo Building Discovery Engine Docker image...
docker build -t autosecure-discovery-engine .

if errorlevel 1 (
    echo.
    echo Error: Failed to build Docker image
    exit /b 1
)

echo.
echo ============================================================
echo Starting Discovery Engine Container
echo ============================================================
echo.
echo The Discovery Engine will scan the Docker bridge network
echo and discover all test devices running in containers.
echo.
echo Network: bridge (Docker default)
echo Duration: 10 seconds
echo.
echo ============================================================
echo.

REM Run Discovery Engine with network access and privileged mode for ARP scanning
docker run -it --rm ^
    --name autosecure-discovery-engine ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    autosecure-discovery-engine

echo.
echo ============================================================
echo Discovery Engine Complete
echo ============================================================
