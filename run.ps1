Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "          ECOGUARD AI - SYSTEM RUNNER (POWERSHELL)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INFO] Kiem tra moi truong he thong..." -ForegroundColor Gray

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Khong tim thay moi truong ao .venv!" -ForegroundColor Red
    exit 1
}

# Ham kiem tra va giai phong cong
function Release-Port {
    param([int]$port)
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pidToKill = $conn[0].OwningProcess
        Write-Host "[WARN] Cong $port dang bi chiem dung boi PID $pidToKill." -ForegroundColor Yellow
        $choice = Read-Host "[?] Giai phong cong nay? Y/N"
        if (($choice -eq "Y") -or ($choice -eq "y")) {
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Da giai phong cong $port." -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host " Chon che do chay:" -ForegroundColor White
Write-Host "   1. Local - Ganache blockchain gia lap, khong can Internet" -ForegroundColor Gray
Write-Host "   2. Sepolia Testnet - Giao dich thuc, hien thi tren Etherscan" -ForegroundColor Gray
Write-Host ""
$mode = Read-Host "[?] Nhap lua chon 1 hoac 2"

if ($mode -eq "2") {
    # ================================================================
    #  CHE DO 2: SEPOLIA TESTNET
    # ================================================================
    Write-Host ""
    Write-Host "[MODE] Chay che do SEPOLIA TESTNET..." -ForegroundColor Cyan
    Write-Host "[INFO] Giao dich se hien thi tren sepolia.etherscan.io" -ForegroundColor Gray
    Write-Host ""

    Release-Port -port 5000

    if (-not (Test-Path ".env")) {
        Write-Host "[ERROR] Khong tim thay file .env!" -ForegroundColor Red
        Write-Host "Vui long tao file .env tu .env.example va dien thong tin Sepolia."
        exit 1
    }

    Write-Host "[1/3] Kiem tra cau hinh Sepolia trong .env..." -ForegroundColor Yellow

    Write-Host ""
    Write-Host " Ban muon lam gi?" -ForegroundColor White
    Write-Host "   A. Deploy contract MOI len Sepolia" -ForegroundColor Gray
    Write-Host "   B. Su dung contract DA CO trong .env" -ForegroundColor Gray
    Write-Host ""
    $deployChoice = Read-Host "[?] Nhap A hoac B"

    if (($deployChoice -eq "A") -or ($deployChoice -eq "a")) {
        Write-Host ""
        Write-Host "[2/3] Deploy Smart Contract len Sepolia Testnet..." -ForegroundColor Yellow
        & .venv\Scripts\python.exe deploy_sepolia.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Loi deploy hop dong len Sepolia." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "[INFO] Su dung CONTRACT_ADDRESS hien tai trong .env." -ForegroundColor Gray
    }

} else {
    # ================================================================
    #  CHE DO 1: LOCAL (GANACHE)
    # ================================================================
    Write-Host ""
    Write-Host "[MODE] Chay che do LOCAL voi Ganache blockchain..." -ForegroundColor Cyan
    Write-Host ""

    if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Khong tim thay Node.js!" -ForegroundColor Red
        exit 1
    }

    Release-Port -port 8545
    Release-Port -port 5000

    Write-Host "[1/4] Khoi chay Ganache Local Blockchain..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npx ganache --host 127.0.0.1 --port 8545 --mnemonic 'eco guard test blockchain development local'"

    Write-Host "[...] Cho Ganache khoi tao cong 8545..." -ForegroundColor Gray
    $retries = 0
    while (-not (Get-NetTCPConnection -LocalPort 8545 -State Listen -ErrorAction SilentlyContinue)) {
        Start-Sleep -Seconds 1
        $retries++
        if ($retries -ge 15) {
            Write-Host "[!] Ganache khong khoi dong duoc sau 15 giay." -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "[OK] Ganache da san sang tren cong 8545!" -ForegroundColor Green

    Write-Host ""
    Write-Host "[2/4] Deploy Smart Contract len Ganache..." -ForegroundColor Yellow
    if (-not (Test-Path .env)) {
        Copy-Item .env.example .env
    }
    & .venv\Scripts\python.exe deploy.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Loi deploy hop dong len Ganache." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# ================================================================
#  KHOI DONG FLASK (CHUNG)
# ================================================================
Write-Host ""
Write-Host "[3/4] Mo giao dien giam sat..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Start-Process "http://localhost:5000"

Write-Host ""
Write-Host "[4/4] Khoi dong Flask Web Server..." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   HE THONG DANG CHAY!" -ForegroundColor Green
Write-Host "   - Web: http://localhost:5000" -ForegroundColor Gray
Write-Host "   - Dong cua so nay de tat Flask." -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

& .venv\Scripts\python.exe app.py
