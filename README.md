<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
 🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<h2 align="center">
    HỆ THỐNG PHÁT HIỆN VỨT RÁC BỪA BÃI BẰNG AI KẾT HỢP BLOCKCHAIN
</h2>
<div align="center">
    <p align="center">
        <img src="aiotlab_logo.png" alt="AIoTLab Logo" width="170"/>
        <img src="fitdnu_logo.png" alt="FIT DNU Logo" width="180"/>
        <img src="dnu_logo.png" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>

## 📖 1. Giới thiệu hệ thống

**EcoGuard AI** là hệ thống giám sát thông minh phát hiện hành vi **vứt rác bừa bãi** theo thời gian thực, kết hợp **AI (YOLOv8)** và **Blockchain (Ethereum Sepolia Testnet)**. Hệ thống cho phép:

    - Phân tích video trực tiếp từ webcam hoặc file video để phát hiện rác, thùng rác và người.

    - Tự động phát hiện vi phạm khi người vứt rác ngoài thùng rác.

    - Chụp ảnh bằng chứng, tính SHA-256 hash và ghi lên Ethereum Blockchain để đảm bảo tính toàn vẹn.

    - Giao diện web dashboard real-time hiển thị thống kê, cảnh báo và lịch sử vi phạm.

Cấu trúc chính:

    - app.py: Ứng dụng Flask chính, xử lý video streaming, API và điều phối toàn bộ hệ thống.

    - blockchain.py: Module tương tác với Ethereum Blockchain (ký giao dịch, ghi vi phạm lên chain).

    - violation.py: Logic phát hiện vi phạm dựa trên khoảng cách người – rác – thùng rác.

    - tracker.py: Thuật toán Centroid Tracking theo dõi đối tượng qua các frame.

    - database.py: CRUD operations với cơ sở dữ liệu SQLite.

    - ViolationRegistry.sol: Smart Contract Solidity lưu trữ bằng chứng trên blockchain.

## 🔧 2. Các công nghệ được sử dụng

- **🤖 YOLOv8 (Ultralytics)** — Nhận diện đối tượng (rác, thùng rác, người)

- **👁️ OpenCV** — Xử lý hình ảnh và video real-time

- **🌐 Flask + Flask-Sock** — Web server và WebSocket streaming

- **💾 SQLite** — Cơ sở dữ liệu lưu trữ vi phạm

- **⛓️ Solidity 0.8.20** — Smart Contract trên Ethereum

- **🔗 Web3.py + ethers.js** — Tương tác blockchain (backend + frontend)

- **🧪 Ethereum Sepolia Testnet** — Mạng blockchain thử nghiệm

- **🐍 Python 3.10+** — Ngôn ngữ lập trình chính

## 🚀 3. Một số hình ảnh hệ thống

<p align="center">
    <em>Giao diện Dashboard chính — Giám sát real-time</em><br/>
    <img width="1401" height="842" alt="Dashboard" src="screenshot_dashboard.png" />
</p>

<p align="center">
    <em>Phát hiện rác và người trên video</em><br/>
    <img width="1401" height="842" alt="Detection" src="screenshot_detection.png" />
</p>

<p align="center">
    <em>Cảnh báo vi phạm vứt rác bừa bãi</em><br/>
    <img width="1401" height="842" alt="Violation Alert" src="screenshot_violation.png" />
</p>

<p align="center">
    <em>Lịch sử vi phạm và bằng chứng Blockchain</em><br/>
    <img width="1401" height="842" alt="Blockchain Evidence" src="screenshot_blockchain.png" />
</p>

---

## ⚙️ 4. Các bước cài đặt

### 4.1. Yêu cầu hệ thống

```
    - Python 3.10 trở lên (kiểm tra bằng lệnh python --version).

    - Cài đặt Git để clone repository.

    - Node.js (nếu sử dụng Ganache local blockchain).

    - MetaMask (nếu sử dụng Sepolia Testnet).

    - Webcam hoặc file video (MP4, MOV, AVI, MKV...) để test.
```

### 4.2. Cấu trúc thư mục

```
EcoGuard-AI/
    │── app.py                    # Ứng dụng Flask chính (entry point)
    │── config.py                 # Cấu hình model và đường dẫn
    │── blockchain.py             # Module tương tác Ethereum Blockchain
    │── database.py               # CRUD operations cho SQLite
    │── violation.py              # Logic phát hiện vi phạm
    │── tracker.py                # Thuật toán tracking đối tượng
    │── detect.py                 # Script phát hiện rác (standalone)
    │── train.py                  # Script huấn luyện model YOLOv8
    │── deploy.py                 # Deploy contract lên Ganache (local)
    │── deploy_sepolia.py         # Deploy contract lên Sepolia Testnet
    │── ViolationRegistry.sol     # Smart Contract Solidity
    │── data.yaml                 # Cấu hình dataset training
    │── run.bat                   # Script chạy tự động (Windows CMD)
    │── run.ps1                   # Script chạy tự động (PowerShell)
    │── .env.example              # Mẫu cấu hình environment
    │── .gitignore                # Danh sách file bỏ qua khi commit
    │
    │── models/                   # Thư mục chứa model AI
    │   ├── nhandienrac.pt        #   Model nhận diện rác VN (custom)
    │   ├── thungrac.pt           #   Model nhận diện thùng rác
    │   └── aquasense/
    │       └── best.pt           #   Model nhận diện chai/lon
    │
    │── templates/
    │   └── index.html            # Dashboard chính (single-page app)
    │
    │── static/violations/        # Ảnh vi phạm phục vụ web
    │── evidence/violations/      # Ảnh gốc vi phạm được lưu
    │── test/                     # Dữ liệu test
    │── valid/                    # Dữ liệu validation
    └── runs/                     # Kết quả training
```

### 4.3. Clone repository và cài đặt

```
    - Clone repository:
        git clone https://github.com/<your-username>/ecoguard-ai.git
        cd ecoguard-ai

    - Tạo môi trường ảo:
        python -m venv .venv
        .venv\Scripts\activate

    - Cài đặt thư viện:
        pip install flask flask-sock ultralytics opencv-python python-dotenv web3 eth-account py-solc-x
```

### 4.4. Cấu hình Blockchain (.env)

```
    - Sao chép file mẫu:
        cp .env.example .env

    - Mở file .env và điền thông tin:
        WALLET_PRIVATE_KEY=your_private_key_here
        SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/your_project_id
        CONTRACT_ADDRESS=0x_your_contract_address

    - Lấy Private Key: MetaMask → Account Details → Show Private Key.
    - Lấy RPC URL: Đăng ký miễn phí tại https://app.infura.io hoặc https://dashboard.alchemy.com.
    - Lấy SepoliaETH miễn phí tại: https://cloud.google.com/application/web3/faucet/ethereum/sepolia.
```

### 4.5. Chạy ứng dụng

```
    Cách 1 — Script tự động (Windows):
        run.bat          (CMD)
        .\run.ps1        (PowerShell)

    Cách 2 — Chạy thủ công:
        .venv\Scripts\activate
        python deploy_sepolia.py    (Tuỳ chọn: deploy smart contract)
        python app.py

    Truy cập giao diện tại: http://localhost:5000
```

---

## 🧠 5. Pipeline AI — Multi-Model YOLOv8

Hệ thống sử dụng **4 model YOLOv8** chạy song song:

| # | Model | File | Kích thước | Chức năng |
|---|-------|------|-----------|-----------|
| 1 | `garbage_model` | `models/nhandienrac.pt` | ~6MB | Nhận diện rác đường phố VN (custom train, ưu tiên cao nhất) |
| 2 | `aquasense_model` | `models/aquasense/best.pt` | ~6MB | Nhận diện chai nhựa, lon, cốc giấy ngoài đường |
| 3 | `bin_model` | `models/thungrac.pt` | ~6MB | Nhận diện 7 loại thùng rác |
| 4 | `person_model` | `yolov8s.pt` | ~22MB | Nhận diện người (COCO pretrained) + rác COCO bổ sung |

**Logic phát hiện vi phạm:** Vi phạm được xác định khi đồng thời thỏa mãn:

    1. Có thùng rác trong camera.
    2. Có người đứng gần thùng rác (≤ 250px).
    3. Có rác gần người đó (≤ 200px).
    4. Rác không nằm trong bounding box thùng rác.
    5. Rác không đang được cầm trên tay.
    6. Chưa báo vi phạm cho rác này trong 10 giây gần nhất (cooldown).

---

## ⛓️ 6. Smart Contract — ViolationRegistry

Smart Contract viết bằng **Solidity 0.8.20**, deploy trên **Ethereum Sepolia Testnet**:

| Function | Mô tả |
|----------|--------|
| `logViolation(violationId, imageHash)` | Ghi vi phạm mới lên blockchain |
| `verifyViolation(violationId, imageHash)` | Xác minh hash ảnh có khớp không |
| `getByViolationId(violationId)` | Lấy thông tin vi phạm theo ID |
| `totalRecords()` | Tổng số vi phạm đã ghi |
| `exists(violationId)` | Kiểm tra vi phạm có tồn tại trên chain không |

**Deploy bằng Remix IDE:**

```
    1. Vào https://remix.ethereum.org
    2. Tạo file ViolationRegistry.sol → Paste nội dung
    3. Compile với Solidity 0.8.20
    4. Deploy với Injected Provider (MetaMask trên Sepolia)
    5. Copy contract address vào file .env
```

---

## 🔌 7. API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| `GET` | `/` | Dashboard chính |
| `GET` | `/video_feed` | MJPEG video stream |
| `GET` | `/snapshot` | Frame JPEG mới nhất |
| `WS` | `/ws_feed` | WebSocket video stream |
| `GET` | `/stats` | Số liệu real-time |
| `GET` | `/violations_data` | Danh sách vi phạm (JSON) |
| `GET` | `/api/list_videos` | Liệt kê file video trong thư mục |
| `POST` | `/api/select_source` | Chuyển nguồn video (webcam/file) |
| `GET` | `/api/blockchain_status` | Trạng thái kết nối blockchain |
| `GET` | `/api/violation_hash/:id` | SHA-256 hash của vi phạm |
| `GET` | `/api/pending_blockchain` | Vi phạm chưa ghi lên blockchain |
| `POST` | `/api/record_blockchain` | Ghi tx_hash sau khi MetaMask confirm |
| `POST` | `/api/check_image_hash` | Upload ảnh kiểm tra tính toàn vẹn |

---

## 📝 8. Liên hệ

- Khoa: Công nghệ thông tin - Trường Đại học Đại Nam
- Lớp: CNTT 16-04
- Tôi: Nguyễn Văn Bắc
- Email: **nguyennbac99@gmail.com**

---

<p align="center">
    ✍️ <em>README này được thiết kế bởi Bac Nguyen</em>
</p>
