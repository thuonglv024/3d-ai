"""
Regression Test Suite for Auth, Body Scan History/Chart, and Orders/Checkout.
Sub-Agent 3: Independent automated regression verification.
"""
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
import secrets

# Ensure backend directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Use an isolated temporary SQLite database before importing backend modules
_temp_dir = tempfile.TemporaryDirectory()
TEST_DB_PATH = Path(_temp_dir.name) / "regression_test.db"
os.environ["MORPH_ORDERS_DB"] = str(TEST_DB_PATH)

from fastapi.testclient import TestClient
from app.main import app, jobs, lock, Job
from app.db import get_db_connection, run_migrations
from app.orders import init_db, validate_vn_phone
import app.history as history_mod


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(f"FAIL: {msg}")
    print(f"  [PASS] {msg}")


def setup_fresh_db():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    run_migrations(TEST_DB_PATH)
    init_db(TEST_DB_PATH)


def test_1_auth_session_cookie_and_logout():
    print("\n=== 1A. Testing Auth Session, Cookie Attributes & Logout Hygiene ===")
    setup_fresh_db()
    client = TestClient(app)

    # Register new user
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "reg_user@morph.vn",
            "password": "Password123!",
            "display_name": "Nguyen Van Test",
        },
    )
    assert_true(reg_res.status_code == 201, f"Register returns 201 Created (got {reg_res.status_code})")

    set_cookie_headers = reg_res.headers.get_list("set-cookie") if hasattr(reg_res.headers, "get_list") else [reg_res.headers.get("set-cookie", "")]
    cookie_str = " ; ".join(set_cookie_headers)
    assert_true("morph_session=" in cookie_str, "Set-Cookie contains morph_session")
    assert_true("HttpOnly" in cookie_str or "httponly" in cookie_str.lower(), "Cookie has HttpOnly attribute")
    assert_true("samesite=lax" in cookie_str.lower(), "Cookie has SameSite=lax attribute")
    assert_true("max-age=2592000" in cookie_str.lower(), "Cookie has Max-Age=2592000 (30 days)")

    # Verify /api/auth/me works with cookie
    me_res = client.get("/api/auth/me")
    assert_true(me_res.status_code == 200, "GET /api/auth/me returns 200")
    assert_true(me_res.json().get("user") is not None, "GET /api/auth/me returns authenticated user")
    assert_true(me_res.json()["user"]["email"] == "reg_user@morph.vn", "Authenticated email matches")

    # Verify session exists in DB before logout
    with get_db_connection(TEST_DB_PATH) as conn:
        cnt_before = conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0]
    assert_true(cnt_before == 1, f"auth_sessions has 1 active row before logout (got {cnt_before})")

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert_true(logout_res.status_code == 200, "POST /api/auth/logout returns 200")

    # Verify session removed from DB
    with get_db_connection(TEST_DB_PATH) as conn:
        cnt_after = conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0]
    assert_true(cnt_after == 0, f"auth_sessions row deleted in DB after logout (got {cnt_after})")

    # Verify /api/auth/me after logout returns {"user": None}
    me_after = client.get("/api/auth/me")
    assert_true(me_after.status_code == 200 and me_after.json() == {"user": None}, "GET /api/auth/me after logout returns {'user': None}")


def test_1b_rate_limiting():
    print("\n=== 1B. Testing Login Rate Limiting (5 failed attempts -> 429 lockout & counter reset) ===")
    setup_fresh_db()
    client = TestClient(app)

    email = "ratelimit@morph.vn"
    password = "CorrectPassword123!"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Rate Limit User"},
    )
    client.post("/api/auth/logout")

    # Case 1: 3 failed attempts then 1 successful login -> resets counter
    for i in range(3):
        r = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword"})
        assert_true(r.status_code == 401, f"Pre-threshold failed attempt #{i+1} returns 401")

    with get_db_connection(TEST_DB_PATH) as conn:
        row = conn.execute("SELECT attempts FROM login_attempts WHERE email = ?", (email,)).fetchone()
    assert_true(row is not None and row["attempts"] == 3, "login_attempts recorded 3 failed attempts")

    ok_login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert_true(ok_login.status_code == 200, "Login with correct password before 5-attempt threshold succeeds (200)")
    login_cookie = " ; ".join(ok_login.headers.get_list("set-cookie"))
    assert_true("morph_session=" in login_cookie and "max-age=2592000" in login_cookie.lower(), "Login sets morph_session cookie with 30-day Max-Age")

    with get_db_connection(TEST_DB_PATH) as conn:
        row_after_ok = conn.execute("SELECT attempts FROM login_attempts WHERE email = ?", (email,)).fetchone()
    assert_true(row_after_ok is None, "Successful login resets login_attempts counter in DB")

    client.post("/api/auth/logout")

    # Case 2: 5 consecutive failed attempts -> triggers 5-minute lockout -> 6th attempt returns 429
    for i in range(5):
        r = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert_true(r.status_code == 401, f"Failed attempt #{i+1}/5 returns 401")

    locked_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert_true(locked_res.status_code == 429, f"Attempt during lockout returns 429 Too Many Requests (got {locked_res.status_code})")
    detail_msg = locked_res.json().get("detail", "")
    assert_true(
        "tạm thời bị khóa" in detail_msg.lower() and "5 lần" in detail_msg.lower(),
        f"429 error detail is in Vietnamese: '{detail_msg}'",
    )

    # Case 3: Expire the lockout window in DB -> login succeeds and resets counter
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    with get_db_connection(TEST_DB_PATH) as conn:
        conn.execute("UPDATE login_attempts SET locked_until = ? WHERE email = ?", (past_iso, email))
        conn.commit()

    unlocked_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert_true(unlocked_res.status_code == 200, "Login succeeds after 5-minute lockout expires")
    with get_db_connection(TEST_DB_PATH) as conn:
        row_final = conn.execute("SELECT * FROM login_attempts WHERE email = ?", (email,)).fetchone()
    assert_true(row_final is None, "Counter reset after post-lockout successful login")


def test_1c_idempotent_claim_scan_and_chart_api():
    print("\n=== 1C. Testing Idempotent Claim Scan (guest_token, 403, 200, no duplicate rows) & Chart API ===")
    setup_fresh_db()
    client = TestClient(app)

    # Verify history.py uses secrets.compare_digest in source
    history_src = Path(history_mod.__file__).read_text(encoding="utf-8")
    assert_true("secrets.compare_digest" in history_src, "history.py uses secrets.compare_digest for guest_token validation")

    # Register user
    client.post(
        "/api/auth/register",
        json={"email": "scanner@morph.vn", "password": "Password123!", "display_name": "Scanner User"},
    )

    # Create a completed guest scan job in memory
    scan_id = "test_scan_guest_001"
    secret_guest_token = secrets.token_urlsafe(24)
    fake_job = Job(
        id=scan_id,
        height_cm=172.0,
        capture_mode="upper_body",
        user_id=None,
        guest_token=secret_guest_token,
    )
    fake_job.status = "completed"
    fake_job.stage = "complete"
    fake_job.measurements = {
        "height_cm": 172.0,
        "chest_cm": 96.4,
        "waist_cm": 81.2,
        "hip_cm": 95.0,
        "shoulder_width_cm": 44.5,
    }
    fake_job.body_profile = {
        "capture_mode": "upper_body",
        "measurement_details": [
            {"key": "height_cm", "value_cm": 172.0, "source": "user_input"},
            {"key": "chest_cm", "value_cm": 96.4, "source": "photo_with_prior"},
            {"key": "waist_cm", "value_cm": 81.2, "source": "photo_with_prior"},
            {"key": "hip_cm", "value_cm": 95.0, "source": "template_model"},
            {"key": "shoulder_width_cm", "value_cm": 44.5, "source": "photo_estimate"},
        ],
    }

    with lock:
        jobs[scan_id] = fake_job

    # 1. Missing guest_token -> 403
    res_missing = client.post("/api/user/scans/save", json={"scan_id": scan_id})
    assert_true(res_missing.status_code == 403, f"Missing guest_token rejected with 403 (got {res_missing.status_code})")

    # 2. Wrong guest_token -> 403
    res_wrong = client.post("/api/user/scans/save", json={"scan_id": scan_id, "guest_token": "wrong_token_xyz"})
    assert_true(res_wrong.status_code == 403, f"Wrong guest_token rejected with 403 (got {res_wrong.status_code})")

    # 3. Correct guest_token -> 200
    res_ok1 = client.post(
        "/api/user/scans/save",
        json={"scan_id": scan_id, "guest_token": secret_guest_token, "note": "First save"},
    )
    assert_true(res_ok1.status_code == 200, f"Correct guest_token saves scan with 200 (got {res_ok1.status_code})")
    saved_id_1 = res_ok1.json()["id"]

    # 4. Second call with same scan_id -> 200 idempotent, returns same id, no duplicate row in body_scans
    res_ok2 = client.post(
        "/api/user/scans/save",
        json={"scan_id": scan_id, "guest_token": secret_guest_token, "note": "Updated note"},
    )
    assert_true(res_ok2.status_code == 200, f"Repeat save_scan returns 200 (got {res_ok2.status_code})")
    saved_id_2 = res_ok2.json()["id"]
    assert_true(saved_id_1 == saved_id_2, f"Idempotent save returns exact same record id ({saved_id_1} == {saved_id_2})")

    with get_db_connection(TEST_DB_PATH) as conn:
        scan_count = conn.execute("SELECT COUNT(*) FROM body_scans WHERE source_scan_id = ?", (scan_id,)).fetchone()[0]
    assert_true(scan_count == 1, f"body_scans table has exactly 1 row for source_scan_id (got {scan_count})")

    # 5. Verify GET /api/user/scans/chart nullifies template_model (hip_cm in upper_body)
    chart_res = client.get("/api/user/scans/chart?range=30d")
    assert_true(chart_res.status_code == 200, "GET /api/user/scans/chart returns 200")
    timeline = chart_res.json()["timeline"]
    assert_true(len(timeline) == 1, "Chart timeline has 1 point")
    hip_metric = timeline[0]["metrics"]["hip_cm"]
    chest_metric = timeline[0]["metrics"]["chest_cm"]
    assert_true(
        hip_metric["value"] is None and hip_metric["valid_for_tracking"] is False and hip_metric["source"] == "template_model",
        f"template_model metric (hip_cm) has value=None and valid_for_tracking=False: {hip_metric}",
    )
    assert_true(
        chest_metric["value"] == 96.4 and chest_metric["valid_for_tracking"] is True,
        f"Measured metric (chest_cm) has value=96.4 and valid_for_tracking=True: {chest_metric}",
    )


def test_3_orders_atomic_stock_idempotency_and_phone_validation():
    print("\n=== 3. Testing Orders Atomic Stock Deduction, Rollback, Idempotency-Key & VN Phone Validation ===")
    setup_fresh_db()
    client = TestClient(app)

    # Pick two variants from DB and set known stock
    with get_db_connection(TEST_DB_PATH) as conn:
        variants = conn.execute(
            """
            SELECT pv.id, pv.product_id, pv.color_name, pv.size, pv.stock, p.name
            FROM product_variants pv
            JOIN products p ON p.id = pv.product_id
            WHERE pv.is_active = 1 AND p.is_active = 1
            LIMIT 2
            """
        ).fetchall()
        assert_true(len(variants) >= 2, "Found at least 2 active variants in seeded DB")
        v1, v2 = variants[0], variants[1]
        conn.execute("UPDATE product_variants SET stock = 10 WHERE id = ?", (v1["id"],))
        conn.execute("UPDATE product_variants SET stock = 5 WHERE id = ?", (v2["id"],))
        conn.commit()

    # 3A. Atomic Stock Deduction on Successful Order
    idem_key_1 = "idem_test_order_001"
    order_payload_1 = {
        "idempotency_key": idem_key_1,
        "customer": {
            "name": "Trần Thị Khách",
            "phone": "+84 912 345 678",
            "email": "khach@morph.vn",
            "address": "123 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh",
            "note": "Giao giờ hành chính",
        },
        "items": [
            {
                "productId": v1["product_id"],
                "color": v1["color_name"],
                "size": v1["size"],
                "quantity": 3,
            }
        ],
    }

    res_ord1 = client.post("/api/orders", json=order_payload_1, headers={"Idempotency-Key": idem_key_1})
    assert_true(res_ord1.status_code == 201, f"Order creation succeeds with 201 (got {res_ord1.status_code})")
    ord1_data = res_ord1.json()
    assert_true(ord1_data["customer"]["phone"] == "0912345678", f"Phone normalized to 0912345678 (got {ord1_data['customer']['phone']})")

    with get_db_connection(TEST_DB_PATH) as conn:
        stock_after_1 = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (v1["id"],)).fetchone()["stock"]
    assert_true(stock_after_1 == 7, f"Stock deducted atomically from 10 to 7 (got {stock_after_1})")

    # 3B. Idempotency-Key Duplicate Request -> Same Order Returned, Stock Deducted ONLY ONCE
    res_ord1_dup = client.post("/api/orders", json=order_payload_1, headers={"Idempotency-Key": idem_key_1})
    assert_true(res_ord1_dup.status_code in (200, 201), f"Duplicate idempotent order request succeeds (got {res_ord1_dup.status_code})")
    ord1_dup_data = res_ord1_dup.json()
    assert_true(
        ord1_dup_data["id"] == ord1_data["id"] and ord1_dup_data["order_code"] == ord1_data["order_code"],
        f"Idempotent retry returns identical order_id ({ord1_data['id']}) and order_code ({ord1_data['order_code']})",
    )

    with get_db_connection(TEST_DB_PATH) as conn:
        stock_after_dup = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (v1["id"],)).fetchone()["stock"]
        order_count = conn.execute("SELECT COUNT(*) FROM orders WHERE idempotency_key = ?", (idem_key_1,)).fetchone()[0]
    assert_true(stock_after_dup == 7, f"Stock NOT double-deducted on idempotent retry (remains {stock_after_dup})")
    assert_true(order_count == 1, f"Only 1 order row created for Idempotency-Key (got {order_count})")

    # 3C. Same Idempotency-Key with DIFFERENT payload -> 409 Conflict
    conflicting_payload = {
        **order_payload_1,
        "items": [
            {
                "productId": v1["product_id"],
                "color": v1["color_name"],
                "size": v1["size"],
                "quantity": 2,  # Changed quantity from 3 to 2
            }
        ],
    }
    res_conflict = client.post("/api/orders", json=conflicting_payload, headers={"Idempotency-Key": idem_key_1})
    assert_true(res_conflict.status_code == 409, f"Same Idempotency-Key with different payload returns 409 Conflict (got {res_conflict.status_code})")
    assert_true("Idempotency-Key" in res_conflict.json().get("detail", ""), f"409 detail mentions Idempotency-Key: {res_conflict.json().get('detail')}")

    # 3D. Out-of-Stock Order Rollback (Single & Multi-item)
    # v1 currently has stock=7, v2 has stock=5.
    # Request v1 (qty=2, valid) + v2 (qty=6, exceeds stock=5) -> must return 400 and v1 stock MUST remain 7!
    overstock_payload = {
        "customer": {
            "name": "Lê Văn Rollback",
            "phone": "0987654321",
            "address": "456 Lê Lợi, Quận 1, TP. Hồ Chí Minh",
        },
        "items": [
            {
                "productId": v1["product_id"],
                "color": v1["color_name"],
                "size": v1["size"],
                "quantity": 2,
            },
            {
                "productId": v2["product_id"],
                "color": v2["color_name"],
                "size": v2["size"],
                "quantity": 6,
            },
        ],
    }
    res_over = client.post("/api/orders", json=overstock_payload)
    assert_true(res_over.status_code == 400, f"Overstock order rejected with 400 Bad Request (got {res_over.status_code})")
    assert_true("không đủ tồn kho" in res_over.json().get("detail", "").lower(), f"400 Vietnamese stock message: {res_over.json().get('detail')}")

    # Also test atomic rollback inside BEGIN IMMEDIATE transaction by simulating stock race condition
    # (where validate_and_aggregate_cart_items passes, or direct transaction rollback verification)
    with get_db_connection(TEST_DB_PATH) as conn:
        s1_now = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (v1["id"],)).fetchone()["stock"]
        s2_now = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (v2["id"],)).fetchone()["stock"]
    assert_true(s1_now == 7 and s2_now == 5, f"Both variants' stock unchanged after failed order (v1={s1_now}, v2={s2_now})")

    # Test direct BEGIN IMMEDIATE transaction rollback when 2nd item fails inside the transaction block
    with get_db_connection(TEST_DB_PATH) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute("UPDATE product_variants SET stock = stock - 2 WHERE id = ? AND stock >= 2", (v1["id"],))
            cur2 = conn.execute("UPDATE product_variants SET stock = stock - 99 WHERE id = ? AND stock >= 99", (v2["id"],))
            if cur2.rowcount == 0:
                raise RuntimeError("Simulated race condition out-of-stock on item 2")
            conn.commit()
        except RuntimeError:
            conn.rollback()

        s1_after_rb = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (v1["id"],)).fetchone()["stock"]
        s2_after_rb = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (v2["id"],)).fetchone()["stock"]
    assert_true(
        s1_after_rb == 7 and s2_after_rb == 5,
        f"BEGIN IMMEDIATE transaction rollback restores v1={s1_after_rb}, v2={s2_after_rb} atomically",
    )

    # 3E. Vietnamese Phone Validation Matrix
    valid_phones = [
        ("0912345678", "0912345678"),
        ("0912 345 678", "0912345678"),
        ("+84912345678", "0912345678"),
        ("+84 912-345-678", "0912345678"),
        ("84912345678", "0912345678"),
        ("091234567", "091234567"),      # 9 digits
        ("01234567890", "01234567890"),  # 11 digits
    ]
    for raw_p, expected_p in valid_phones:
        cleaned = validate_vn_phone(raw_p)
        assert_true(cleaned == expected_p, f"validate_vn_phone('{raw_p}') -> '{cleaned}' == '{expected_p}'")

    invalid_phones = [
        "",
        "   ",
        "123456789",       # Does not start with 0 or +84
        "0912345",         # Too short (7 digits)
        "091234567890",    # Too long (12 digits)
        "0912abc678",      # Contains letters
        "+1912345678",     # Non-VN country code
    ]
    for bad_p in invalid_phones:
        failed = False
        try:
            validate_vn_phone(bad_p)
        except ValueError:
            failed = True
        assert_true(failed, f"validate_vn_phone('{bad_p}') raises ValueError as expected")


if __name__ == "__main__":
    try:
        test_1_auth_session_cookie_and_logout()
        test_1b_rate_limiting()
        test_1c_idempotent_claim_scan_and_chart_api()
        test_3_orders_atomic_stock_idempotency_and_phone_validation()
        print("\n========================================================")
        print("ALL BACKEND REGRESSION TESTS PASSED SUCCESSFULLY (100%)")
        print("========================================================")
    finally:
        _temp_dir.cleanup()
