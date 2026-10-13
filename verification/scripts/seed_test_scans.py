import sqlite3
import uuid
import sys

def seed_user_scans(user_id: str):
    conn = sqlite3.connect('D:/MORPH-AI/.runtime/orders.db')
    conn.execute('DELETE FROM body_scans WHERE user_id = ?', (user_id,))

    scanA = f'scan_a_{uuid.uuid4().hex[:8]}'
    scanB = f'scan_b_{uuid.uuid4().hex[:8]}'
    scanC = f'scan_c_{uuid.uuid4().hex[:8]}'

    # Scan A (10 days ago, upper_body)
    conn.execute('''
      INSERT INTO body_scans (id, user_id, source_scan_id, captured_at, saved_at, capture_mode, height_input_cm, engine_version, measurement_schema_version, warnings, note)
      VALUES (?, ?, ?, '2026-10-03T10:00:00Z', '2026-10-03T10:02:00Z', 'upper_body', 165.0, 'v1.2-morph', 1, '[]', 'Scan ngày 03/10')
    ''', (scanA, user_id, scanA))
    for mk, val, src in [
        ('chest_cm', 86.0, 'photo_with_prior'),
        ('waist_cm', 66.0, 'photo_with_prior'),
        ('hip_cm', None, 'template_model'),
        ('shoulder_width_cm', 38.5, 'photo_with_prior'),
        ('height_cm', 165.0, 'user_input'),
    ]:
        conn.execute('INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)',
                     (uuid.uuid4().hex, scanA, mk, val, src))

    # Scan B (Today 09:00:00, full_body)
    conn.execute('''
      INSERT INTO body_scans (id, user_id, source_scan_id, captured_at, saved_at, capture_mode, height_input_cm, engine_version, measurement_schema_version, warnings, note)
      VALUES (?, ?, ?, '2026-10-13T09:00:00Z', '2026-10-13T09:02:00Z', 'full_body', 165.0, 'v1.2-morph', 1, '[]', 'Scan toàn thân sáng nay')
    ''', (scanB, user_id, scanB))
    for mk, val, src in [
        ('chest_cm', 86.5, 'photo_estimate'),
        ('waist_cm', 65.5, 'photo_estimate'),
        ('hip_cm', 91.0, 'photo_estimate'),
        ('shoulder_width_cm', 38.6, 'photo_estimate'),
        ('height_cm', 165.0, 'user_input'),
    ]:
        conn.execute('INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)',
                     (uuid.uuid4().hex, scanB, mk, val, src))

    # Scan C (Today 09:05:00, full_body - within 5 min of B!)
    conn.execute('''
      INSERT INTO body_scans (id, user_id, source_scan_id, captured_at, saved_at, capture_mode, height_input_cm, engine_version, measurement_schema_version, warnings, note)
      VALUES (?, ?, ?, '2026-10-13T09:05:00Z', '2026-10-13T09:07:00Z', 'full_body', 165.0, 'v1.2-morph', 1, '[]', 'Scan đối chứng 5 phút sau')
    ''', (scanC, user_id, scanC))
    for mk, val, src in [
        ('chest_cm', 86.4, 'photo_estimate'),
        ('waist_cm', 65.6, 'photo_estimate'),
        ('hip_cm', 91.2, 'photo_estimate'),
        ('shoulder_width_cm', 38.6, 'photo_estimate'),
        ('height_cm', 165.0, 'user_input'),
    ]:
        conn.execute('INSERT INTO body_measurements (id, body_scan_id, metric_key, value_cm, source) VALUES (?, ?, ?, ?, ?)',
                     (uuid.uuid4().hex, scanC, mk, val, src))

    conn.commit()
    conn.close()
    print("SEEDED_OK for user:", user_id)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        seed_user_scans(sys.argv[1])
    else:
        print("Please provide user_id")
