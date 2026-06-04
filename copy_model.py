import os
import shutil
import glob

def copy_best_model():
    best_candidates = glob.glob("models/trash_detection*/weights/best.pt")
    
    if not best_candidates:
        print("⚠️  Chưa tìm thấy best.pt. Training có thể chưa xong hoặc chưa tạo checkpoint.")
        return

    # Lấy file mới nhất nếu có nhiều run
    best_src = max(best_candidates, key=os.path.getmtime)
    dest = "models/best.pt"

    shutil.copy2(best_src, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"✅ Đã copy model thành công!")
    print(f"   Nguồn : {best_src}")
    print(f"   Đích   : {dest}")
    print(f"   Kích thước: {size_mb:.2f} MB")

if __name__ == "__main__":
    copy_best_model()
