@echo off
REM Complete AutoSecure Test - Devices + Main Engine Pipeline

echo ============================================================
echo         AutoSecure - Complete Testing Environment
echo ============================================================
echo.
echo This script will:
echo   1. Start all test devices in Docker containers
echo   2. Wait for devices to initialize
echo   3. Run the Main Engine pipeline
echo   4. Display results
echo.
echo ============================================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [Step 1/3] Starting test devices...
echo.

cd Devices
call run-all-devices.bat

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start devices
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [Step 2/3] Waiting for devices to initialize...
echo ============================================================
echo.
timeout /t 5 /nobreak >nul

echo Devices are ready!
echo.
echo ============================================================
echo [Step 3/3] Running AutoSecure Engines (Discovery + Segmentation)...
echo ============================================================
echo.

cd ..\Engines
call run-engines.bat

echo.
echo ============================================================
echo                Test Complete!
echo ============================================================
echo.
echo All devices are still running.
echo.
echo Options:
echo   - Run again:            cd Engines ^&^& run-engines.bat
echo   - View device logs:     docker logs autosecure-mdns-generic-1
echo   - List all devices:     cd Devices ^&^& list-devices.bat
echo   - Stop all devices:     cd Devices ^&^& stop-all-devices.bat
echo.
echo ============================================================
echo.

cd ..
pause
