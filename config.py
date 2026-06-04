# Configuration for illegal dump detection
# ════════════════════════════════════════════════════════════════════
#  Chiến lược model đã tối ưu:
#  1. garbage_model  = nhandienrac.pt        (custom VN, 6MB, 1 cls)
#  2. aquasense_model= aquasense/best.pt     (chai/lon, 6MB, 5 cls)
#  3. bin_model      = thungrac.pt           (thùng rác, 6MB, 7 cls)
#  4. person_model   = yolov8s.pt            (COCO, detect người)
# ════════════════════════════════════════════════════════════════════

# ── Model custom của bạn – train trên dữ liệu thực tế VN (ưu tiên cao nhất)
GARBAGE_MODEL = "models/nhandienrac.pt"

# ── Model nhận diện chai/lon ngoài đường phố (thay thế waste-classification)
#    Nhẹ hơn 8x (6MB vs 48.8MB), phù hợp hơn với rác ngoài đường
#    Classes: aluminum_soda_cans, glass_beverage_bottles, paper_cups,
#             plastic_soda_bottles, plastic_water_bottles
AQUASENSE_MODEL = "models/aquasense/best.pt"

# ── [KHÔNG CÒN DÙNG] waste-classification – 48.8MB, train trong studio
#    → Đã thay bằng aquasense_model cho hiệu năng tốt hơn
TRASH_MODEL = "models/waste-classification/yolov8n-waste-12cls-best.pt"  # giữ lại để tham khảo

# Database name
DB_NAME = "violations.db"

# Evidence directory
EVIDENCE_DIR = "evidence/violations"
