@echo off
REM Run AutoSecure Engines (Discovery + Segmentation) in Docker

echo Building AutoSecure Engines Docker image...
docker build -t autosecure-engines .

if errorlevel 1 (
    echo.
    echo Error: Failed to build Docker image
    exit /b 1
)

echo.
echo ============================================================
echo Starting AutoSecure Engines Container
echo ============================================================
echo.
echo Running Discovery + Segmentation on the Docker bridge network.
echo.
echo ============================================================
echo.

REM Run with network access and privileged mode for ARP scanning + iptables
docker run -it --rm ^
    --name autosecure-engines ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    autosecure-engines

echo.
echo ============================================================
echo AutoSecure Engines Complete
echo ============================================================
