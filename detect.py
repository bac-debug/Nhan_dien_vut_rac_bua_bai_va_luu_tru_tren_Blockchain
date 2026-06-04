import cv2
import os
import datetime
from ultralytics import YOLO

from tracker import SimpleTracker
from violation import detect_violation
from database import create_table, save_violation
from config import TRASH_CLASSES, TRASH_MODEL

# ── Model nhận dạng RÁC (TACO dataset – Hugging Face, 18 class rác ngoài trời)
print("[INFO] Đang load model nhận diện rác (TACO dataset)...")
trash_model = YOLO(TRASH_MODEL)
print(f"[INFO] Trash classes: {list(trash_model.names.values())}")

# ── Model nhận dạng NGƯỜI (YOLOv8 COCO – có sẵn class "person")
person_model = YOLO("yolov8n.pt")

# Tạo bảng database nếu chưa tồn tại
create_table()

tracker = SimpleTracker()

os.makedirs("evidence/violations", exist_ok=True)

cap = cv2.VideoCapture("IMG_2364.MOV")
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Ngăn chặn delay frame

while True:
    ret, frame = cap.read()

    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Quay về frame đầu
        continue

    # Resize giảm kích thước hình ảnh để giảm tải cho CPU
    frame = cv2.resize(frame, (640, 480))

    # ── Nhận dạng NGƯỜI bằng model COCO (hạ imgsz xuống 320 để tăng tốc)
    person_results = person_model(frame, classes=[0], imgsz=320, verbose=False)[0]  # class 0 = person

    # ── Nhận dạng RÁC bằng model custom (hạ imgsz xuống 320)
    trash_results = trash_model(frame, imgsz=320, verbose=False)[0]

    person_boxes = []
    trash_boxes = []

    # --- Xử lý kết quả NGƯỜI ---
    for box in person_results.boxes:
        cls_id = int(box.cls[0])
        class_name = person_model.names[cls_id]

        if class_name == "person":
            conf = float(box.conf[0])
            if conf < 0.5:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w = x2 - x1
            h = y2 - y1
            person_boxes.append([x1, y1, w, h])

    # --- Xử lý kết quả RÁC ---
    for box in trash_results.boxes:
        cls_id = int(box.cls[0])
        class_name = trash_model.names[cls_id]

        # TRASH_CLASSES = None → chấp nhận tất cả (TACO model chỉ detect rác)
        if TRASH_CLASSES is None or class_name in TRASH_CLASSES:
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w = x2 - x1
            h = y2 - y1
            trash_boxes.append([x1, y1, w, h])

            # Vẽ bounding box RÁC (màu xanh lá)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{class_name} {conf:.2f}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # ── Theo dõi NGƯỜI qua các frame
    tracked_persons = tracker.update(person_boxes)

    for p in tracked_persons:
        x, y, w, h, pid = p

        # Vẽ bounding box NGƯỜI (màu xanh dương)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.putText(frame, f"Person {pid}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # ── Phát hiện vi phạm (người gần rồi bỏ rác)
    violations = detect_violation(tracked_persons, trash_boxes)

    for pid in violations:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = f"evidence/violations/{pid}_{timestamp}.jpg"

        cv2.imwrite(image_path, frame)
        save_violation(pid, image_path, timestamp)

        print(f"[!] Vi phạm phát hiện: Person {pid} tại {timestamp}")

        # Hiển thị cảnh báo đỏ trên màn hình
        cv2.putText(frame, f"VIOLATION! Person {pid}",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 3)

    # Hiển thị số người và số rác trên màn hình
    cv2.putText(frame, f"Persons: {len(tracked_persons)}",
                (10, frame.shape[0] - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, f"Trash: {len(trash_boxes)}",
                (10, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imshow("Illegal Dump Detection", frame)

    if cv2.waitKey(1) == 27:  # Nhấn ESC để thoát
        break

cap.release()
cv2.destroyAllWindows()
