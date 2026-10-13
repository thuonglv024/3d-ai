import sqlite3
import uuid
import sys

def seed(user_id: str):
    conn = sqlite3.connect(r'D:/MORPH-AI/.runtime/orders.db')

    # Scan 1: Earlier scan (2026-10-01)
    sid1 = 'scan-demo-01'
    conn.execute('''
    INSERT OR REPLACE INTO body_scans (
        id, user_id, source_scan_id, captured_at, saved_at,
        capture_mode, height_input_cm, engine_version, measurement_schema_version, warnings, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    ''', (sid1, user_id, sid1, '2026-10-01T08:30:00Z', '2026-10-01T08:32:00Z', 'upper_body', 168.0, 'v1.2-morph', '[]', 'Đo buổi sáng trước khi tập'))

    conn.execute('DELETE FROM body_measurements WHERE body_scan_id = ?', (sid1,))
    for mk, val, src in [
        ('height_cm', 168.0, 'user_input'),
        ('chest_cm', 88.0, 'photo_with_prior'),
        ('waist_cm', 68.5, 'photo_with_prior'),
        ('hip_cm', None, 'template_model'),
        ('shoulder_width_cm', 39.5, 'photo_with_prior'),
    ]:
        conn.execute('INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)',
                     (str(uuid.uuid4()), sid1, mk, val, src))

    # Scan 2: Later scan (2026-10-13)
    sid2 = 'scan-demo-02'
    conn.execute('''
    INSERT OR REPLACE INTO body_scans (
        id, user_id, source_scan_id, captured_at, saved_at,
        capture_mode, height_input_cm, engine_version, measurement_schema_version, warnings, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    ''', (sid2, user_id, sid2, '2026-10-13T09:15:00Z', '2026-10-13T09:17:00Z', 'upper_body', 168.0, 'v1.2-morph', '[]', 'Đo lại sau 2 tuần'))

    conn.execute('DELETE FROM body_measurements WHERE body_scan_id = ?', (sid2,))
    for mk, val, src in [
        ('height_cm', 168.0, 'user_input'),
        ('chest_cm', 88.5, 'photo_with_prior'),
        ('waist_cm', 67.2, 'photo_with_prior'),
        ('hip_cm', None, 'template_model'),
        ('shoulder_width_cm', 39.8, 'photo_with_prior'),
    ]:
        conn.execute('INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)',
                     (str(uuid.uuid4()), sid2, mk, val, src))

    conn.commit()
    conn.close()
    print("Seeding demo scans complete for user:", user_id)

if __name__ == '__main__':
    uid = sys.argv[1] if len(sys.argv) > 1 else 'b38c2006bb2140849013edbc11c7475a'
    seed(uid)
