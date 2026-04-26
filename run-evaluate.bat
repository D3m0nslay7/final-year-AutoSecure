@echo off
REM AutoSecure — Metrics Evaluation
REM ============================================================
REM Measures two metrics with the full system running:
REM
REM   Metric 1: Time to Detection (TTD)
REM             Seconds from attack launch to first alert
REM
REM   Metric 2: Threat Detection Rate (TDR)
REM             %% of attack categories that triggered an alert
REM
REM WITHOUT AutoSecure baseline: TTD = infinite, TDR = 0%%
REM
REM Prerequisites:
REM   - Docker Desktop running
REM   - Device containers already started (run Devices\run-all-devices.bat first)
REM
REM Timeline:
REM    0s  — engines evaluation container starts
REM    ~5s — attacks fire automatically from inside the eval container
REM   90s  — monitoring ends; metrics report printed to console
REM          results also saved to Evaluation\results.json
REM ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo        AutoSecure - Metrics Evaluation
echo ============================================================
echo.

REM ── Check Docker ─────────────────────────────────────────────────────────
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Start Docker Desktop and try again.
    pause
    exit /b 1
)

REM ── Check devices are up ─────────────────────────────────────────────────
echo Checking device containers...
docker ps --filter name=autosecure-mdns-generic-1 --format "{{.Names}}" 2>nul | findstr autosecure >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Device containers are not running.
    echo Please run Devices\run-all-devices.bat first, wait 5 seconds, then re-run.
    echo.
    pause
    exit /b 1
)
echo   OK — devices are running.
echo.

echo Device IPs will be resolved automatically inside the evaluation container.
echo.

REM ── Clean up leftover containers from previous runs ───────────────────────
docker rm -f autosecure-eval-run >nul 2>&1
docker rm -f autosecure-attacks-eval >nul 2>&1

REM ── Build engines image ───────────────────────────────────────────────────
echo [1/3] Building engines image...
cd Engines
docker build -t autosecure-engines . >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to build engines image.
    cd ..
    pause
    exit /b 1
)
cd ..
echo   Done.

REM ── Build attacks image ───────────────────────────────────────────────────
echo [2/3] Building attacks image...
docker build -t autosecure-attacks -f Attacks/Dockerfile.attacks Attacks/ >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to build attacks image.
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Run evaluation ────────────────────────────────────────────────────────
echo [3/3] Running evaluation (90 second monitoring window)...
echo   The script will auto-launch attacks after 5 seconds.
echo   Please wait — this takes ~90 seconds.
echo.
echo ============================================================

REM The eval container:
REM   - runs evaluate_metrics.py (mounted from ./Evaluation/)
REM   - has Docker socket access so it can launch the attacks container
REM   - gets device IPs as env vars
REM   - writes results.json back to ./Evaluation/ via the volume mount
docker run --rm ^
    --name autosecure-eval-run ^
    --network bridge ^
    --cap-add=NET_ADMIN ^
    --cap-add=NET_RAW ^
    -v //var/run/docker.sock:/var/run/docker.sock ^
    -v "%~dp0Evaluation":/app/Evaluation ^
    --network autosecure-net ^
    autosecure-engines ^
    python -u /app/Evaluation/evaluate_metrics.py

echo.
echo ============================================================
if exist "%~dp0Evaluation\results.json" (
    echo   Results saved to: Evaluation\results.json
) else (
    echo   Note: results.json not written — check output above for errors.
)
echo ============================================================
echo.
pause
