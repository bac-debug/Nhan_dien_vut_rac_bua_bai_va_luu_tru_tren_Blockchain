import sqlite3

DB_NAME = "violations.db"


def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Bảng violations với 2 cột mới hỗ trợ blockchain
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id   INTEGER,
            image_path  TEXT,
            timestamp   TEXT,
            image_hash  TEXT,    -- SHA-256 hash của ảnh bằng chứng
            tx_hash     TEXT     -- Transaction hash sau khi ghi lên blockchain
        )
    """)

    # Migration: thêm cột nếu table đã tồn tại từ phiên bản cũ
    try:
        cursor.execute("ALTER TABLE violations ADD COLUMN image_hash TEXT")
    except Exception:
        pass  # Cột đã tồn tại
    try:
        cursor.execute("ALTER TABLE violations ADD COLUMN tx_hash TEXT")
    except Exception:
        pass  # Cột đã tồn tại

    conn.commit()
    conn.close()


def save_violation(person_id, image_path, timestamp, image_hash=None):
    """Lưu vi phạm mới, tuỳ chọn kèm hash ảnh."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO violations(person_id, image_path, timestamp, image_hash)
        VALUES (?, ?, ?, ?)
    """, (person_id, image_path, timestamp, image_hash))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_all_violations():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, person_id, image_path, timestamp, image_hash, tx_hash FROM violations")
    data = cursor.fetchall()
    conn.close()
    return data


def get_violation_by_id(violation_id):
    """Lấy thông tin 1 vi phạm theo ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, person_id, image_path, timestamp, image_hash, tx_hash FROM violations WHERE id = ?",
        (violation_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def find_by_hash(image_hash: str):
    """
    Tìm vi phạm theo SHA-256 hash của ảnh.
    Trả về tuple (id, person_id, image_path, timestamp, image_hash, tx_hash)
    hoặc None nếu không tìm thấy.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, person_id, image_path, timestamp, image_hash, tx_hash "
        "FROM violations WHERE image_hash = ? LIMIT 1",
        (image_hash,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_tx_hash(violation_id, tx_hash):
    """Cập nhật transaction hash sau khi ghi lên blockchain thành công."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE violations SET tx_hash = ? WHERE id = ?",
        (tx_hash, violation_id)
    )
    conn.commit()
    conn.close()
