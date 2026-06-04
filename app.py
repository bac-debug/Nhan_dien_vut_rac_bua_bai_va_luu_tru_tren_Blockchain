import cv2
import os
import time
import datetime
import hashlib
import threading
from flask import Flask, render_template, Response, send_from_directory, jsonify, make_response, request
from flask_sock import Sock

from ultralytics import YOLO
from tracker import SimpleTracker
from violation import detect_violation
from database import create_table, save_violation, get_all_violations, get_violation_by_id, update_tx_hash, find_by_hash
from config import AQUASENSE_MODEL
import blockchain

app = Flask(__name__)
sock = Sock(app)

# ── Khởi tạo database
create_table()
os.makedirs("evidence/violations", exist_ok=True)
os.makedirs("static/violations", exist_ok=True)

# ── Thư mục gốc dự án (cùng chỗ với app.py) – đặt video tại đây là tự động nhận
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}

# ── Khởi tạo kết nối Blockchain (tự động, không chặn)
print("[INFO] Khởi tạo kết nối blockchain...")
blockchain.init_blockchain()

# ── Load models
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  Chiến lược model (đã tối ưu):                                          │
# │  garbage_model   ← nhandienrac.pt   (custom VN, 6MB, 1 cls: Trash)     │
# │  aquasense_model ← aquasense/best.pt(6MB, 5 cls: chai/lon đường phố)   │
# │  bin_model       ← thungrac.pt      (6MB, 7 cls: thùng rác)            │
# │  person_model    ← yolov8s.pt       (COCO general, detect người+COCO)  │
# └─────────────────────────────────────────────────────────────────────────┘

# Model 1 ─ garbage_model: Model custom train đặc biệt cho ngữ cảnh VN
#   Classes: ['Trash'] – nhận diện túi rác, rác bừa bãi trên đường phố VN
print("[INFO] Đang load garbage_model (custom VN - nhandienrac.pt)...")
garbage_model = YOLO("models/nhandienrac.pt")
print(f"[INFO] garbage_model OK ✓  Classes: {list(garbage_model.names.values())}")

# Model 2 ─ aquasense_model: Nhận diện chai/lon ngoài đường phố (6MB, nhanh)
#   Classes: aluminum_soda_cans, glass_beverage_bottles, paper_cups,
#            plastic_soda_bottles, plastic_water_bottles
#   → Thay thế waste-classification (48.8MB, train trong studio) để:
#     • Giảm RAM ~43MB
#     • Phù hợp hơn với rác ngoài đường (chai nhựa, lon, cốc giấy)
print("[INFO] Đang load aquasense_model (street bottles/cans - aquasense/best.pt)...")
aquasense_model = YOLO(AQUASENSE_MODEL)
print(f"[INFO] aquasense_model OK ✓  Classes: {list(aquasense_model.names.values())}")

# Model 3 ─ bin_model + person_model
bin_model    = YOLO("models/thungrac.pt")
person_model = YOLO("yolov8s.pt")
print("[INFO] Tất cả model đã sẵn sàng.")

# Các class COCO bổ sung (tập trung loại rác phổ biến ngoài đường)
COCO_TRASH_CLASSES = {
    26: "tú xach",     # tú (có thể là tú rác)
    39: "chai",         # chai nước
    41: "cốc",          # cốc nhựa
    46: "vỏ chuối",    # vỏ trái cây
    52: "vỏ cam",      # vỏ cam quýt
}

# ── Biến global
output_frame = None
raw_frame = None
frame_lock = threading.Lock()
data_lock = threading.Lock()

current_source = 0  # 0: webcam, hoặc đường dẫn file video
source_changed = False

stats = {"bins": 0, "trash": 0, "persons": 0, "violations": 0}
latest_boxes = {
    "bins": [],
    "trash": [],
    "persons": [],
    "violation_alert": ""
}
violation_alert_end_time = 0

def camera_thread():
    """Vòng lặp đọc camera liên tục (nhanh) và vẽ hình để stream mượt nhất"""
    global raw_frame, output_frame, current_source, source_changed

    PLAYBACK_SPEED = 0.75  # Tốc độ phát video (0.75 = chậm hơn 25%)

    # Khởi tạo nguồn ban đầu
    cap = cv2.VideoCapture(current_source)
    video_fps = 30  # mặc định
    if isinstance(current_source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
    else:
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30

    while True:
        if source_changed:
            print(f"[INFO] Chuyển đổi nguồn video thành: {current_source}")
            cap.release()
            cap = cv2.VideoCapture(current_source)
            if isinstance(current_source, int):
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                video_fps = 30
            else:
                video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
                print(f"[INFO] Video FPS gốc: {video_fps:.1f}, tốc độ phát: {PLAYBACK_SPEED}x")
            source_changed = False
            time.sleep(0.5)
            continue

        ret, frame = cap.read()
        if not ret:
            # Nếu là file video, tự động lặp lại từ đầu
            if not isinstance(current_source, int):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                time.sleep(0.03)  # Tránh chiếm dụng CPU quá mức
                continue
            # Webcam bị ngắt – thử kết nối lại sau 1 giây
            print("[WARN] Không đọc được frame từ webcam, thử lại...")
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(current_source)
            if isinstance(current_source, int):
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
            continue

        # Giữ kích thước gốc video, không resize cứng
        # (Webcam đã set 640x480 ở trên, video file giữ nguyên resolution)

        # Nếu là file video → delay theo FPS gốc x tốc độ phát
        if not isinstance(current_source, int):
            delay = 1.0 / (video_fps * PLAYBACK_SPEED)
            time.sleep(delay)
        
        with data_lock:
            raw_frame = frame.copy()
            boxes = latest_boxes.copy()
            alert_end = violation_alert_end_time
            
        # ── Vẽ bounding boxes ──
        for t in boxes["trash"]:
            x1, y1, x2, y2, cls_name, conf = t
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 50), 2)
            cv2.putText(frame, f"{cls_name} {conf:.2f}", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 50), 2)
            
        for b in boxes["bins"]:
            x1, y1, x2, y2 = b
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, "Bin", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        for p in boxes["persons"]:
            x1, y1, x2, y2, conf = p
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 140, 0), 2)
            cv2.putText(frame, f"Person {conf:.2f}", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 140, 0), 2)
            
        # ── Cảnh báo vi phạm (hiển thị trong 2 giây) ──
        if time.time() < alert_end and boxes["violation_alert"]:
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 60), (0, 0, 180), -1)
            cv2.putText(frame, boxes["violation_alert"], (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            
        # ── Ghi ra output_frame cho WebSocket ──
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with frame_lock:
            output_frame = buffer.tobytes()
            
    cap.release()

def inference_thread():
    """Vòng lặp YOLO (chậm hơn) chạy song song lấy frame mới nhất để phân tích"""
    global raw_frame, latest_boxes, stats, violation_alert_end_time
    
    tracker        = SimpleTracker()
    person_tracker = SimpleTracker()
    
    while True:
        with data_lock:
            if raw_frame is None:
                frame_to_process = None
            else:
                frame_to_process = raw_frame.copy()
                
        if frame_to_process is None:
            time.sleep(0.01)
            continue
            
        # Chạy model nhận dạng (theo thứ tự ưu tiên)
        bin_results       = bin_model(frame_to_process,       imgsz=320, verbose=False)[0]
        garbage_results   = garbage_model(frame_to_process,   imgsz=320, verbose=False)[0]  # custom VN – ưu tiên cao nhất
        aquasense_results = aquasense_model(frame_to_process, imgsz=320, verbose=False)[0]  # chai/lon đường phố
        coco_results      = person_model(frame_to_process,    imgsz=320, verbose=False)[0]  # COCO general

        bin_boxes                = []
        trash_boxes_for_tracker  = []
        trash_boxes_for_draw     = []
        person_boxes_for_tracker = []
        person_boxes_for_draw    = []

        # ── Bin detection ──
        for box in bin_results.boxes:
            conf = float(box.conf[0])
            if conf < 0.4:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bin_boxes.append([x1, y1, x2, y2])

        # ── 0. garbage_model (QUAN TRỌNG NHẤT): Model custom train trên dữ liệu VN
        #   → Nhận diện rác bừa bãi trên đường phố Việt Nam chính xác nhất
        for box in garbage_results.boxes:
            cls_name = garbage_model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            if conf < 0.3:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            trash_boxes_for_tracker.append([x1, y1, x2 - x1, y2 - y1])
            trash_boxes_for_draw.append((x1, y1, x2, y2, f"[VN]{cls_name}", conf))

        # ── 1. aquasense_model: Nhận diện chai nhựa, lon, cốc giấy ngoài đường
        #   → Thay thế waste-classification (48.8MB) – nhẹ hơn 8x, phù hợp đường phố hơn
        for box in aquasense_results.boxes:
            cls_name = aquasense_model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            if conf < 0.35:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            trash_boxes_for_tracker.append([x1, y1, x2 - x1, y2 - y1])
            trash_boxes_for_draw.append((x1, y1, x2, y2, f"[CHAI]{cls_name}", conf))

        # ── 2. COCO model: bổ sung detect rác phổ biến (chai, cốc, tú…)
        for box in coco_results.boxes:
            cls_id = int(box.cls[0])
            if cls_id == 0:  # bỏ qua class "person"
                continue
            if cls_id not in COCO_TRASH_CLASSES:
                continue
            conf = float(box.conf[0])
            if conf < 0.4:
                continue
            cls_name = COCO_TRASH_CLASSES[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            trash_boxes_for_tracker.append([x1, y1, x2 - x1, y2 - y1])
            trash_boxes_for_draw.append((x1, y1, x2, y2, f"[COCO]{cls_name}", conf))

        # ── 3. Lấy kết quả detect người (class 0) từ COCO model
        for box in coco_results.boxes:
            cls_id = int(box.cls[0])
            if cls_id != 0:          # class 0 = person trong COCO
                continue
            conf = float(box.conf[0])
            if conf < 0.4:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            person_boxes_for_tracker.append([x1, y1, x2 - x1, y2 - y1])
            person_boxes_for_draw.append((x1, y1, x2, y2, conf))

        tracked_trashes = tracker.update(trash_boxes_for_tracker)
        tracked_persons = person_tracker.update(person_boxes_for_tracker)
        violations = detect_violation(tracked_trashes, bin_boxes, tracked_persons)
        
        alert_msg = ""
        for tid in violations:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trash_{tid}_{timestamp}.jpg"
            image_path = f"evidence/violations/{filename}"
            static_path = f"static/violations/{filename}"

            cv2.imwrite(image_path, frame_to_process)
            cv2.imwrite(static_path, frame_to_process)

            # ── Tính SHA-256 hash của ảnh bằng chứng để ghi lên blockchain
            image_hash = None
            try:
                with open(image_path, "rb") as f:
                    image_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception as e:
                print(f"[WARN] Không tính được hash ảnh: {e}")

            new_id = save_violation(tid, image_path, timestamp, image_hash)
            stats["violations"] += 1
            print(f"[!] VI PHAM: Rac ID {tid} luc {timestamp} | hash={image_hash[:16] if image_hash else 'N/A'}...")

            # ── Tự động ghi lên blockchain (chạy trong thread riêng, không block AI)
            if image_hash and new_id:
                def _on_chain_success(tx_hex, vid=new_id):
                    update_tx_hash(vid, tx_hex)
                    print(f"[BLOCKCHAIN] DB cập nhật tx_hash cho vi phạm #{vid}")

                blockchain.record_violation_on_chain(
                    violation_id=new_id,
                    image_hash=image_hash,
                    on_success=_on_chain_success
                )

            alert_msg = f"!! VI PHAM: Rac #{tid} bi vut bua bai !!"
            
        with data_lock:
            latest_boxes["bins"]    = bin_boxes
            latest_boxes["trash"]   = trash_boxes_for_draw
            latest_boxes["persons"] = person_boxes_for_draw
            if alert_msg:
                latest_boxes["violation_alert"] = alert_msg
                violation_alert_end_time = time.time() + 2.0
                
        stats["bins"]    = len(bin_boxes)
        stats["trash"]   = len(trash_boxes_for_draw)
        stats["persons"] = len(person_boxes_for_draw)


def generate_frames():
    """Generator stream MJPEG cho Flask (fallback)"""
    global output_frame
    while True:
        with frame_lock:
            if output_frame is None:
                time.sleep(0.01)
                continue
            frame_bytes = output_frame
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.016)  # ~60fps cap to prevent CPU waste


# ── Routes ──────────────────────────────────────────

@app.route("/")
def index():
    violations = get_all_violations()
    return render_template("index.html", violations=violations)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/snapshot")
def snapshot():
    """Trả về frame JPEG mới nhất — dùng cho JS polling (mượt hơn MJPEG)"""
    with frame_lock:
        if output_frame is None:
            return '', 204
        frame_bytes = output_frame
    response = make_response(frame_bytes)
    response.headers['Content-Type'] = 'image/jpeg'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['X-Timestamp'] = str(time.time())
    return response


@sock.route("/ws_feed")
def ws_feed(ws):
    """Gửi frame liên tục qua WebSocket để giảm độ trễ và tải mạng"""
    global output_frame
    while True:
        with frame_lock:
            if output_frame is None:
                time.sleep(0.01)
                continue
            frame_bytes = output_frame
        try:
            ws.send(frame_bytes)
            time.sleep(0.016)  # Điều tiết tốc độ xấp xỉ 60 FPS
        except Exception:
            break


@app.route("/stats")
def get_stats():
    """API trả về số liệu realtime (dùng bởi JS polling)"""
    stats_copy = stats.copy()
    if current_source == 0:
        stats_copy["source"] = "webcam"
        stats_copy["source_label"] = "Webcam trực tiếp"
    else:
        stats_copy["source"] = str(current_source)
        stats_copy["source_label"] = os.path.basename(str(current_source))
    return jsonify(stats_copy)


@app.route("/api/select_source", methods=["POST"])
def select_source():
    global current_source, source_changed
    body = request.get_json(force=True)
    src_type = body.get("source", "webcam")

    if src_type == "webcam":
        current_source = 0
    else:
        # src_type là filename – tìm trong thư mục gốc dự án (BASE_DIR)
        full_path = os.path.join(BASE_DIR, src_type)
        if not os.path.isfile(full_path):
            return jsonify({"error": f"Không tìm thấy file video: {src_type}"}), 400
        current_source = full_path

    source_changed = True
    label = "webcam" if current_source == 0 else os.path.basename(str(current_source))
    print(f"[INFO] Yêu cầu chuyển nguồn video sang: {current_source}")
    return jsonify({"status": "ok", "source": label})


@app.route("/api/list_videos")
def list_videos():
    """Liệt kê tất cả file video trong thư mục dự án (cùng chỗ app.py).
    Chỉ cần copy/đặt file video vào thư mục này là tự động xuất hiện trong danh sách."""
    videos = []
    for fname in sorted(os.listdir(BASE_DIR)):
        full_path = os.path.join(BASE_DIR, fname)
        if os.path.isfile(full_path) and os.path.splitext(fname)[1].lower() in ALLOWED_VIDEO_EXTS:
            videos.append({
                "filename": fname,
                "size_mb": round(os.path.getsize(full_path) / (1024 * 1024), 2)
            })
    return jsonify(videos)


@app.route("/violations_data")
def violations_data():
    """API trả về danh sách vi phạm mới nhất (có thêm hash và tx_hash cho blockchain)"""
    rows = get_all_violations()
    data = [{
        "id":        r[0],
        "person_id": r[1],
        "image":     r[2].replace("evidence/", "static/"),
        "time":      r[3],
        "hash":      r[4] or "",          # SHA-256 của ảnh
        "tx_hash":   r[5] or ""           # Transaction hash trên blockchain
    } for r in rows]
    return jsonify(data)


@app.route("/evidence/<path:filename>")
def serve_evidence(filename):
    return send_from_directory("evidence", filename)


# ══ Blockchain API Routes ═══════════════════════════════════════════════

@app.route("/api/violation_hash/<int:violation_id>")
def api_violation_hash(violation_id):
    """Trả về SHA-256 hash của ảnh vi phạm – frontend dùng để ghi lên blockchain."""
    row = get_violation_by_id(violation_id)
    if row is None:
        return jsonify({"error": "Không tìm thấy vi phạm"}), 404
    return jsonify({
        "id":        row[0],
        "person_id": row[1],
        "image":     row[2].replace("evidence/", "static/"),
        "timestamp": row[3],
        "hash":      row[4] or "",
        "tx_hash":   row[5] or ""
    })


@app.route("/api/record_blockchain", methods=["POST"])
def api_record_blockchain():
    """
    Frontend gọi sau khi giao dịch MetaMask thành công.
    Body JSON: { "violation_id": 1, "tx_hash": "0xabc..." }
    """
    body = request.get_json(force=True)
    violation_id = body.get("violation_id")
    tx_hash      = body.get("tx_hash", "").strip()

    if not violation_id or not tx_hash:
        return jsonify({"error": "Thiếu violation_id hoặc tx_hash"}), 400

    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return jsonify({"error": "tx_hash không hợp lệ"}), 400

    update_tx_hash(violation_id, tx_hash)
    print(f"[BLOCKCHAIN] Vi phạm #{violation_id} đã ghi lên chain: {tx_hash}")
    return jsonify({"status": "ok", "violation_id": violation_id, "tx_hash": tx_hash})


@app.route("/api/pending_blockchain")
def api_pending_blockchain():
    """Trả về danh sách vi phạm chưa được ghi lên blockchain (tx_hash rỗng)."""
    rows = get_all_violations()
    pending = [{
        "id":        r[0],
        "person_id": r[1],
        "timestamp": r[3],
        "hash":      r[4] or ""
    } for r in rows if not r[5]]  # chưa có tx_hash
    return jsonify(pending)


@app.route("/api/blockchain_status")
def api_blockchain_status():
    """Trả về trạng thái kết nối blockchain (dùng bởi frontend để hiển thị UI)."""
    return jsonify(blockchain.get_status())


@app.route("/api/check_image_hash", methods=["POST"])
def api_check_image_hash():
    """
    Kiểm tra xem ảnh upload có khớp với bất kỳ vi phạm nào đã lưu không.
    Request: multipart/form-data với field 'image'
    Response: JSON { found, violation | null, hash }
    """
    if 'image' not in request.files:
        return jsonify({"error": "Không có file ảnh được gửi lên"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Chưa chọn file ảnh"}), 400

    try:
        img_bytes = file.read()
        image_hash = hashlib.sha256(img_bytes).hexdigest()
    except Exception as e:
        return jsonify({"error": f"Không đọc được file ảnh: {e}"}), 500

    row = find_by_hash(image_hash)

    if row is None:
        return jsonify({
            "found":     False,
            "hash":      image_hash,
            "violation": None
        })

    viol_id, person_id, img_path, timestamp, _, tx_hash = row
    time_formatted = timestamp  # giữ nguyên dạng YYYYMMDD_HHMMSS
    return jsonify({
        "found":     True,
        "hash":      image_hash,
        "violation": {
            "id":        viol_id,
            "person_id": person_id,
            "image":     img_path.replace("evidence/", "static/"),
            "timestamp": timestamp,
            "tx_hash":   tx_hash or ""
        }
    })


# ── Khởi động các luồng xử lý ──
camera_t = threading.Thread(target=camera_thread, daemon=True)
camera_t.start()

inference_t = threading.Thread(target=inference_thread, daemon=True)
inference_t.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
