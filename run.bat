@echo off
title EcoGuard AI System Runner
color 0B

echo ==========================================================
echo           ECOGUARD AI - SYSTEM RUNNER (WINDOWS)
echo ==========================================================
echo.

echo [INFO] Kiem tra moi truong he thong...

if not exist .venv\Scripts\python.exe (
    echo [ERROR] Khong tim thay moi truong ao .venv!
    echo Vui long tao moi truong ao va cai dat thu vien truoc.
    pause
    exit /b 1
)

echo.
echo  Chon che do chay:
echo    1. Local - Ganache blockchain gia lap, khong can Internet
echo    2. Sepolia Testnet - Giao dich thuc, hien thi tren Etherscan
echo.
set /p "MODE=[?] Nhap lua chon 1 hoac 2: "

if "%MODE%"=="2" goto MODE_SEPOLIA

:: ================================================================
::  CHE DO 1: LOCAL (GANACHE)
:: ================================================================
:MODE_LOCAL
echo.
echo [MODE] Chay che do LOCAL voi Ganache blockchain...
echo.

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay Node.js. Vui long cai dat Node.js de chay Ganache!
    pause
    exit /b 1
)

echo [INFO] Kiem tra cac cong ket noi...

:: Kiem tra cong 8545 (Ganache)
set "PORT_8545_PID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /c:"LISTENING" ^| findstr /r /c:":8545 "') do (
    set "PORT_8545_PID=%%a"
)
if not defined PORT_8545_PID goto LOCAL_CHECK_5000

echo [WARN] Cong 8545 dang bi chiem dung boi PID %PORT_8545_PID%.
set /p "CHOICE_8545=[?] Giai phong cong nay? Y/N: "
if /i "%CHOICE_8545%"=="Y" (
    taskkill /f /pid %PORT_8545_PID% >nul 2>nul
    echo [OK] Da giai phong cong 8545.
)

:LOCAL_CHECK_5000

:: Kiem tra cong 5000 (Flask)
set "PORT_5000_PID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /c:"LISTENING" ^| findstr /r /c:":5000 "') do (
    set "PORT_5000_PID=%%a"
)
if not defined PORT_5000_PID goto LOCAL_START_GANACHE

echo [WARN] Cong 5000 dang bi chiem dung boi PID %PORT_5000_PID%.
set /p "CHOICE_5000=[?] Giai phong cong nay? Y/N: "
if /i "%CHOICE_5000%"=="Y" (
    taskkill /f /pid %PORT_5000_PID% >nul 2>nul
    echo [OK] Da giai phong cong 5000.
)

:LOCAL_START_GANACHE
echo.
echo [1/4] Khoi chay Ganache Local Blockchain...
start "EcoGuard Ganache Node" cmd /k npx ganache --host 127.0.0.1 --port 8545 --mnemonic "eco guard test blockchain development local"

echo [...] Cho Ganache khoi tao cong 8545...
set "RETRIES=0"
:LOCAL_WAIT
timeout /t 1 /nobreak > nul
set "IS_OPEN="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /c:"LISTENING" ^| findstr /r /c:":8545 "') do (
    set "IS_OPEN=%%a"
)
if defined IS_OPEN goto LOCAL_GANACHE_OK
set /a RETRIES+=1
if %RETRIES% geq 15 (
    echo [!] Ganache khong khoi dong duoc sau 15 giay.
    pause
    exit /b 1
)
goto LOCAL_WAIT

:LOCAL_GANACHE_OK
echo [OK] Ganache da san sang tren cong 8545!

echo.
echo [2/4] Deploy Smart Contract len Ganache...
if not exist .env (
    copy .env.example .env > nul
)
.venv\Scripts\python.exe deploy.py
if %errorlevel% neq 0 (
    echo [ERROR] Loi deploy hop dong len Ganache.
    pause
    exit /b %errorlevel%
)

goto START_FLASK

:: ================================================================
::  CHE DO 2: SEPOLIA TESTNET
:: ================================================================
:MODE_SEPOLIA
echo.
echo [MODE] Chay che do SEPOLIA TESTNET...
echo [INFO] Giao dich se hien thi tren sepolia.etherscan.io
echo.

:: Kiem tra cong 5000 (Flask)
set "PORT_5000_PID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /c:"LISTENING" ^| findstr /r /c:":5000 "') do (
    set "PORT_5000_PID=%%a"
)
if not defined PORT_5000_PID goto SEPOLIA_CHECK_ENV

echo [WARN] Cong 5000 dang bi chiem dung boi PID %PORT_5000_PID%.
set /p "CHOICE_5000=[?] Giai phong cong nay? Y/N: "
if /i "%CHOICE_5000%"=="Y" (
    taskkill /f /pid %PORT_5000_PID% >nul 2>nul
    echo [OK] Da giai phong cong 5000.
)

:SEPOLIA_CHECK_ENV
if not exist .env (
    echo [ERROR] Khong tim thay file .env!
    echo Vui long tao file .env tu .env.example va dien thong tin Sepolia.
    pause
    exit /b 1
)

echo [1/3] Kiem tra cau hinh Sepolia trong .env...

:: Hoi nguoi dung co muon deploy contract moi khong
echo.
echo  Ban muon lam gi?
echo    A. Deploy contract MOI len Sepolia - lan dau hoac muon tao contract moi
echo    B. Su dung contract DA CO trong .env - da deploy truoc do
echo.
set /p "DEPLOY_CHOICE=[?] Nhap A hoac B: "

if /i "%DEPLOY_CHOICE%"=="A" (
    echo.
    echo [2/3] Deploy Smart Contract len Sepolia Testnet...
    .venv\Scripts\python.exe deploy_sepolia.py
    if %errorlevel% neq 0 (
        echo [ERROR] Loi deploy hop dong len Sepolia.
        pause
        exit /b %errorlevel%
    )
) else (
    echo [INFO] Su dung CONTRACT_ADDRESS hien tai trong .env.
)

goto START_FLASK

:: ================================================================
::  KHOI DONG FLASK (CHUNG CHO CA 2 CHE DO)
:: ================================================================
:START_FLASK
echo.
echo [3/4] Mo giao dien giam sat...
timeout /t 2 /nobreak > nul
start http://localhost:5000

echo.
echo [4/4] Khoi dong Flask Web Server...
echo ==========================================================
echo    HE THONG DANG CHAY!
echo    - Web: http://localhost:5000
echo    - Dong cua so nay de tat Flask.
echo ==========================================================
echo.
.venv\Scripts\python.exe app.py
pause
