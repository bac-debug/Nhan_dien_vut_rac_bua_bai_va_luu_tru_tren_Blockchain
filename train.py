from ultralytics import YOLO
import os
import shutil
import glob

def train_model():
    model = YOLO("yolov8n.pt")

    print("Bắt đầu quá trình huấn luyện mô hình...")
    
    results = model.train(
        data="data.yaml",       
        epochs=50,              
        imgsz=640,              
        batch=16,               
        project="models",       
        name="trash_detection", 
        device='cpu',          
        save=True
    )
    print("Huấn luyện hoàn tất!")

    # Tìm và copy best.pt sang models/best.pt
    best_candidates = glob.glob("models/trash_detection*/weights/best.pt")
    if best_candidates:
        # Lấy file mới nhất nếu có nhiều run
        best_src = max(best_candidates, key=os.path.getmtime)
        dest = "models/best.pt"
        shutil.copy2(best_src, dest)
        print(f"✅ Đã copy model: {best_src} -> {dest}")
    else:
        print("⚠️  Không tìm thấy best.pt để copy.")

if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)
    train_model()