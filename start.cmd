@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if exist "%ROOT%.venv313\Scripts\python.exe" set "PYTHON=%ROOT%.venv313\Scripts\python.exe"
set "NEED_PIP=0"
set "API_PID="
set "WEB_PID="

if not exist "%PYTHON%" (
  where py >nul 2>nul
  if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 (
      echo Python was not found. Install Python and try again.
      goto :failed
    )
    python -m venv "%ROOT%.venv"
  ) else (
    py -3 -m venv "%ROOT%.venv"
  )
  if errorlevel 1 goto :failed
  set "NEED_PIP=1"
)

if "%NEED_PIP%"=="1" goto :install_python
"%PYTHON%" -c "import fastapi, httpx, jwt, pydantic_settings, uvicorn" >nul 2>nul
if errorlevel 1 goto :install_python
goto :python_ready

:install_python
echo [setup] Installing backend dependencies...
"%PYTHON%" -m pip install -r "%ROOT%backend\requirements.txt"
if errorlevel 1 goto :failed

:python_ready
"%PYTHON%" "%ROOT%backend\tools\bootstrap_config.py"
if errorlevel 1 goto :failed

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Install Node.js and try again.
  goto :failed
)
where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Install Node.js with npm and try again.
  goto :failed
)
if not exist "%ROOT%frontend\node_modules" (
  echo [setup] Installing frontend dependencies...
  call npm.cmd --prefix "%ROOT%frontend" ci
  if errorlevel 1 goto :failed
)

netstat -ano | findstr /R /C:":8958 .*LISTENING" >nul
if not errorlevel 1 (
  echo Port 8958 is already in use. Close the other service and try again.
  goto :failed
)
netstat -ano | findstr /R /C:":8959 .*LISTENING" >nul
if not errorlevel 1 (
  echo Port 8959 is already in use. Close the other service and try again.
  goto :failed
)

echo [start] API: http://127.0.0.1:8959
pushd "%ROOT%backend"
start "" /b "%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8959
popd
set /a WAIT_COUNT=0

:wait_api
netstat -ano | findstr /R /C:":8959 .*LISTENING" >nul
if not errorlevel 1 goto :api_ready
set /a WAIT_COUNT+=1
if %WAIT_COUNT% GEQ 40 (
  echo FastAPI did not start. Check the messages above.
  goto :stop_services
)
timeout /t 1 /nobreak >nul
goto :wait_api

:api_ready
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8959 .*LISTENING"') do set "API_PID=%%P"
echo [start] Web: http://127.0.0.1:8958
pushd "%ROOT%frontend"
start "" /b node "%ROOT%frontend\node_modules\vite\bin\vite.js" --host 127.0.0.1 --port 8958
popd
set /a WAIT_COUNT=0

:wait_web
netstat -ano | findstr /R /C:":8958 .*LISTENING" >nul
if not errorlevel 1 goto :web_ready
set /a WAIT_COUNT+=1
if %WAIT_COUNT% GEQ 40 (
  echo Vue did not start. Check the messages above.
  goto :stop_services
)
timeout /t 1 /nobreak >nul
goto :wait_web

:web_ready
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8958 .*LISTENING"') do set "WEB_PID=%%P"
start "" "http://127.0.0.1:8958"
echo.
echo Minecraft-Link is running. Close this window to stop the services.
echo Web: http://127.0.0.1:8958
echo API: http://127.0.0.1:8959
echo API docs: docs\api.md and the Web console sidebar at http://127.0.0.1:8958

:monitor
timeout /t 2 /nobreak >nul
netstat -ano | findstr /R /C:":8958 .*LISTENING" >nul
if errorlevel 1 goto :stop_services
netstat -ano | findstr /R /C:":8959 .*LISTENING" >nul
if errorlevel 1 goto :stop_services
goto :monitor

:stop_services
echo Stopping Minecraft-Link services...
if defined WEB_PID taskkill /PID %WEB_PID% /T /F >nul 2>nul
if defined API_PID taskkill /PID %API_PID% /T /F >nul 2>nul
echo Minecraft-Link has stopped.
pause
exit /b 0

:failed
echo.
echo Startup failed. Press any key to close this window.
pause >nul
exit /b 1
