import os
import shutil
import yaml

# Đường dẫn tới thư mục TrashBox của bạn
source_dir = "TrashBox-main/TrashBox_train_dataset_subfolders"
# Đường dẫn chuẩn YOLO sẽ tạo ra
dest_images_dir = "datasets/images/train"
dest_labels_dir = "datasets/labels/train"

os.makedirs(dest_images_dir, exist_ok=True)
os.makedirs(dest_labels_dir, exist_ok=True)

classes = []
class_id = 0

print("Bắt đầu chuyển đổi dữ liệu...")

# Quét qua các thư mục
for root, dirs, files in os.walk(source_dir):
    # Lọc ra những thư mục chứa file ảnh (bỏ qua thư mục cha không chứa ảnh)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if image_files:
        # Lấy tên thư mục hiện tại làm tên class
        class_name = os.path.basename(root)
        classes.append(class_name)
        
        for img in image_files:
            # Đổi tên file để tránh trùng lặp khi gom vào chung 1 folder
            new_img_name = f"{class_name}_{img}"
            shutil.copy2(os.path.join(root, img), os.path.join(dest_images_dir, new_img_name))
            
            # TẠO FILE LABEL TRỐNG (Yêu cầu bắt buộc của YOLO)
            # Lưu ý: Vì bạn chưa có file tọa độ, ta tạo file .txt trống tạm thời
            txt_name = new_img_name.rsplit('.', 1)[0] + '.txt'
            open(os.path.join(dest_labels_dir, txt_name), 'w').close()
            
        print(f"Đã xử lý class: {class_name} - {len(image_files)} ảnh")
        class_id += 1

# Tự động tạo file data.yaml
yaml_data = {
    'path': 'datasets',
    'train': 'images/train',
    'val': 'images/train', # Dùng tạm tập train làm val nếu chưa chia
    'names': {i: name for i, name in enumerate(classes)}
}

with open('data.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)

print("\nHoàn tất! Đã tạo xong file data.yaml và cấu trúc thư mục YOLO chuẩn.")