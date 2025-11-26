@echo off
REM List all running AutoSecure test device containers

echo ============================================================
echo     Running AutoSecure Test Device Containers
echo ============================================================
echo.

docker ps --filter name=autosecure- --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ============================================================
echo.
echo Total containers running:
for /f %%i in ('docker ps -q --filter name=autosecure- ^| find /c /v ""') do echo   %%i
echo.
