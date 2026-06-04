import time
import math

# Lưu trạng thái vi phạm: {trash_id: last_violation_time}
violated_trash_ids = {}

VIOLATION_COOLDOWN = 10    # giây: mỗi rác chỉ báo lại sau 10s
PERSON_BIN_DIST   = 250    # px: người phải đứng trong phạm vi này với thùng rác
PERSON_TRASH_DIST = 200    # px: rác phải gần người trong phạm vi này


def _center(x, y, w, h):
    return (x + w // 2, y + h // 2)


def _dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def detect_violation(tracked_trashes, bins, tracked_persons):
    """
    Phát hiện vi phạm vứt rác ngoài thùng:
      - CÓ thùng rác trong camera.
      - CÓ người đứng gần thùng rác (trong PERSON_BIN_DIST px).
      - CÓ rác gần người đó (trong PERSON_TRASH_DIST px).
      - Rác KHÔNG nằm trong bbox thùng rác.
    => VI PHẠM.
    """
    violations = []
    now = time.time()

    # Nếu không có thùng rác trong frame → bỏ qua
    if not bins:
        return violations

    # Tính tâm các thùng rác
    bin_centers = [((bx1 + bx2) // 2, (by1 + by2) // 2) for bx1, by1, bx2, by2 in bins]

    # Tìm những người đứng gần ít nhất 1 thùng rác
    persons_near_bin = []
    for px, py, pw, ph, pid in tracked_persons:
        pc = _center(px, py, pw, ph)
        for bc in bin_centers:
            if _dist(pc, bc) <= PERSON_BIN_DIST:
                persons_near_bin.append((px, py, pw, ph, pc))
                break

    # Nếu không có người nào đứng gần thùng → bỏ qua
    if not persons_near_bin:
        return violations

    # Kiểm tra từng rác được phát hiện
    for tx, ty, tw, th, tid in tracked_trashes:
        # Kiểm tra cooldown
        if now - violated_trash_ids.get(tid, 0) < VIOLATION_COOLDOWN:
            continue

        trash_center = _center(tx, ty, tw, th)

        # Rác có gần người nào đứng cạnh thùng không và có bị cầm không?
        near_person = False
        is_held = False
        for px, py, pw, ph, pc in persons_near_bin:
            if _dist(trash_center, pc) <= PERSON_TRASH_DIST:
                near_person = True
                # Nếu tâm rác nằm trong phần trên của người (từ đầu đến 80% chiều cao)
                # => Rác đang được người cầm, chưa bỏ xuống đất
                if (px - 20 <= trash_center[0] <= px + pw + 20) and (py <= trash_center[1] <= py + ph * 0.8):
                    is_held = True

        if not near_person:
            continue
            
        if is_held:
            continue # Đang cầm trên tay, chưa bỏ xuống

        # Rác có nằm trong thùng nào không? (cho phép sai số 20px)
        in_bin = False
        for bx1, by1, bx2, by2 in bins:
            if (bx1 - 20 <= trash_center[0] <= bx2 + 20 and
                    by1 - 20 <= trash_center[1] <= by2 + 20):
                in_bin = True
                break

        # Người đứng gần thùng + rác gần người + rác nằm NGOÀI thùng => VI PHẠM
        if not in_bin:
            violations.append(tid)
            violated_trash_ids[tid] = now

    return violations