import cv2
import os
import time
import datetime
import threading
from flask import Flask, render_template, Response, send_from_directory, jsonify, make_response
from flask_sock import Sock

from ultralytics import YOLO
from tracker import SimpleTracker
from violation import detect_violation
from database import create_table, save_violation, get_all_violations
from config import TRASH_CLASSES

app = Flask(__name__)
sock = Sock(app)

# ── Khởi tạo database
create_table()
os.makedirs("evidence/violations", exist_ok=True)
os.makedirs("static/violations", exist_ok=True)

# ── Load models
trash_model = YOLO("models/best.pt")
person_model = YOLO("yolov8n.pt")

# ── Biến global để chia sẻ frame giữa thread và Flask
output_frame = None
frame_lock = threading.Lock()
stats = {"persons": 0, "trash": 0, "violations": 0}


def detection_loop():
    """Vòng lặp detect chạy trong background thread"""
    global output_frame, stats

    tracker = SimpleTracker()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Khử độ trễ (latency lag) bằng cách không cho lưu frame cũ


    while True:
        ret, frame = cap.read()

        # Khi video hết thì loop lại từ đầu
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # Resize giảm kích thước hình ảnh
        frame = cv2.resize(frame, (640, 480))

        # Nhận dạng NGƯỜI và RÁC (hạ imgsz=320 để đạt tốc độ tối đa)
        person_results = person_model(frame, classes=[0], imgsz=320, verbose=False)[0]
        trash_results  = trash_model(frame, imgsz=320, verbose=False)[0]

        person_boxes = []
        trash_boxes  = []

        # Xử lý bounding box NGƯỜI
        for box in person_results.boxes:
            if person_model.names[int(box.cls[0])] == "person":
                conf = float(box.conf[0])
                if conf < 0.5:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                person_boxes.append([x1, y1, x2 - x1, y2 - y1])

        # Xử lý bounding box RÁC
        for box in trash_results.boxes:
            cls_name = trash_model.names[int(box.cls[0])]
            if cls_name in TRASH_CLASSES:
                conf = float(box.conf[0])
                if conf < 0.4:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                trash_boxes.append([x1, y1, x2 - x1, y2 - y1])

                # Vẽ rác — màu xanh lá
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 50), 2)
                label = f"{cls_name} {conf:.2f}"
                cv2.putText(frame, label, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 50), 2)

        # Theo dõi NGƯỜI
        tracked_persons = tracker.update(person_boxes)

        for p in tracked_persons:
            x, y, w, h, pid = p
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 100, 0), 2)
            cv2.putText(frame, f"Person {pid}", (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 2)

        # Phát hiện vi phạm
        violations = detect_violation(tracked_persons, trash_boxes)

        for pid in violations:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pid}_{timestamp}.jpg"
            image_path = f"evidence/violations/{filename}"
            static_path = f"static/violations/{filename}"

            # Lưu ảnh vi phạm
            cv2.imwrite(image_path, frame)
            cv2.imwrite(static_path, frame)

            save_violation(pid, image_path, timestamp)
            stats["violations"] += 1
            print(f"[!] VI PHAM: Person {pid} luc {timestamp}")

            # Cảnh báo đỏ trên frame
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 60), (0, 0, 180), -1)
            cv2.putText(frame, f"!! VIOLATION - Person {pid} !!",
                        (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

        # Cập nhật stats
        stats["persons"] = len(tracked_persons)
        stats["trash"]   = len(trash_boxes)

        # HUD thông tin
        h_frame = frame.shape[0]
        cv2.rectangle(frame, (0, h_frame - 50), (300, h_frame), (30, 30, 30), -1)
        cv2.putText(frame, f"Persons: {len(tracked_persons)}  Trash: {len(trash_boxes)}",
                    (8, h_frame - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)

        # Ghi frame ra biến global (encode JPEG)
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with frame_lock:
            output_frame = buffer.tobytes()

    cap.release()


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
    return jsonify(stats)


@app.route("/violations_data")
def violations_data():
    """API trả về danh sách vi phạm mới nhất"""
    rows = get_all_violations()
    data = [{"id": r[0], "person_id": r[1],
             "image": r[2].replace("evidence/", "static/"),
             "time": r[3]} for r in rows]
    return jsonify(data)


@app.route("/evidence/<path:filename>")
def serve_evidence(filename):
    return send_from_directory("evidence", filename)


# ── Khởi động detection thread ──
thread = threading.Thread(target=detection_loop, daemon=True)
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
