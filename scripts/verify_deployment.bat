@echo off
REM ============================================================
REM BKO Station - Deployment Verification Script (Windows)
REM Usage: verify_deployment.bat [backend_url] [frontend_url]
REM Example: verify_deployment.bat https://bko-station-production.up.railway.app https://bko-station-frontend.vercel.app
REM ============================================================

setlocal enabledelayedexpansion

set BACKEND_URL=%~1
set FRONTEND_URL=%~2

if "%BACKEND_URL%"=="" set BACKEND_URL=http://localhost:8000
if "%FRONTEND_URL%"=="" set FRONTEND_URL=http://localhost:8080

set PASS=0
set FAIL=0
set WARN=0

echo ============================================================
echo   BKO Station - Deployment Verification
echo ============================================================
echo Backend URL:  %BACKEND_URL%
echo Frontend URL: %FRONTEND_URL%
echo ============================================================
echo.

REM --------------------------------------------------------
REM 1. Backend Health Check
REM --------------------------------------------------------
echo --- Backend Health ---
curl -sf "%BACKEND_URL%/api/health/" > "%TEMP%\health.json" 2>nul
if exist "%TEMP%\health.json" (
    type "%TEMP%\health.json" | findstr "healthy" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Health endpoint reachable
        set /a PASS+=1
        type "%TEMP%\health.json"
    ) else (
        echo [FAIL] Health endpoint returned unexpected content
        set /a FAIL+=1
    )
    del "%TEMP%\health.json" >nul 2>&1
) else (
    echo [FAIL] Health endpoint not reachable
    set /a FAIL+=1
)

echo.

REM --------------------------------------------------------
REM 2. API Stations Endpoint
REM --------------------------------------------------------
echo --- Stations API ---
curl -sf "%BACKEND_URL%/api/stations/" > "%TEMP%\stations.json" 2>nul
if exist "%TEMP%\stations.json" (
    type "%TEMP%\stations.json" | findstr "count" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Stations endpoint reachable
        set /a PASS+=1
    ) else (
        echo [WARN] Stations endpoint response unexpected
        set /a WARN+=1
    )
    del "%TEMP%\stations.json" >nul 2>&1
) else (
    echo [FAIL] Stations endpoint not reachable
    set /a FAIL+=1
)

echo.

REM --------------------------------------------------------
REM 3. Auth Token Endpoint
REM --------------------------------------------------------
echo --- Auth Token Endpoint ---
curl -sf -X POST "%BACKEND_URL%/api/auth/token/" -H "Content-Type: application/json" -d "{\"username\":\"test\",\"password\":\"test\"}" > "%TEMP%\token.json" 2>nul
if exist "%TEMP%\token.json" (
    echo [PASS] Token endpoint reachable
    set /a PASS+=1
    del "%TEMP%\token.json" >nul 2>&1
) else (
    echo [WARN] Token endpoint response unexpected
    set /a WARN+=1
)

echo.

REM --------------------------------------------------------
REM 4. Statistics Endpoint
REM --------------------------------------------------------
echo --- Statistics API ---
curl -sf "%BACKEND_URL%/api/statistics/" > "%TEMP%\stats.json" 2>nul
if exist "%TEMP%\stats.json" (
    echo [PASS] Statistics endpoint reachable
    set /a PASS+=1
    del "%TEMP%\stats.json" >nul 2>&1
) else (
    echo [FAIL] Statistics endpoint not reachable
    set /a FAIL+=1
)

echo.

REM --------------------------------------------------------
REM 5. Frontend Reachable
REM --------------------------------------------------------
echo --- Frontend ---
curl -sf "%FRONTEND_URL%/" > "%TEMP%\front.html" 2>nul
if exist "%TEMP%\front.html" (
    type "%TEMP%\front.html" | findstr "Bamako Gaz Tracker" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Frontend serving HTML correctly
        set /a PASS+=1
    ) else (
        echo [FAIL] Frontend not serving expected content
        set /a FAIL+=1
    )
    del "%TEMP%\front.html" >nul 2>&1
) else (
    echo [FAIL] Frontend not reachable
    set /a FAIL+=1
)

echo.

REM --------------------------------------------------------
REM 6. Frontend Config
REM --------------------------------------------------------
echo --- Frontend Config ---
curl -sf "%FRONTEND_URL%/config.js" > "%TEMP%\config.js" 2>nul
if exist "%TEMP%\config.js" (
    type "%TEMP%\config.js" | findstr "API_BASE_URL" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Frontend config.js contains API_BASE_URL
        set /a PASS+=1
    ) else (
        echo [WARN] Frontend config.js may not have API_BASE_URL
        set /a WARN+=1
    )
    del "%TEMP%\config.js" >nul 2>&1
) else (
    echo [WARN] Frontend config.js not reachable
    set /a WARN+=1
)

echo.

REM --------------------------------------------------------
REM Summary
REM --------------------------------------------------------
echo ============================================================
echo   Verification Summary
echo ============================================================
echo   Passed: %PASS%
echo   Failed: %FAIL%
echo   Warnings: %WARN%
echo ============================================================

if %FAIL% gtr 0 (
    echo Some checks failed. Review the output above.
    exit /b 1
) else (
    echo All critical checks passed!
    exit /b 0
)
