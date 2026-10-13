"""Authentication, session management, and user profile module for MORPH AI."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
from pathlib import Path
import re
import secrets
from typing import Optional, Union
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from .db import get_db_connection, get_db_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE_NAME = "morph_session"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 3600  # 30 days = 2,592,000s
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5


# --- Password Hashing Utilities ---
def hash_password(password: str) -> str:
    """Hashes password with PBKDF2-HMAC-SHA256 and a random 16-byte salt."""
    salt = secrets.token_bytes(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${hash_bytes.hex()}"


def verify_password(plain_password: str, hashed: str) -> bool:
    """Verifies a plain password against stored salt$hash representation."""
    try:
        if not hashed or "$" not in hashed:
            return False
        salt_hex, hash_hex = hashed.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000).hex()
        return hmac.compare_digest(computed, hash_hex)
    except Exception:
        return False


def hash_session_token(token: str) -> str:
    """Returns SHA256 hex digest of session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- Rate Limiting Utilities ---
def check_login_rate_limit(conn, ip: str, email: str) -> None:
    """Checks whether the ip/email pair is currently locked out."""
    now = datetime.now(timezone.utc)
    row = conn.execute(
        "SELECT attempts, locked_until FROM login_attempts WHERE ip = ? AND email = ?",
        (ip, email),
    ).fetchone()
    if row and row["locked_until"]:
        try:
            locked_dt = datetime.fromisoformat(row["locked_until"])
            if locked_dt > now:
                remaining_sec = int((locked_dt - now).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Tài khoản tạm thời bị khóa do nhập sai mật khẩu quá {MAX_FAILED_ATTEMPTS} lần. Vui lòng thử lại sau {max(1, remaining_sec)} giây.",
                )
        except HTTPException:
            raise
        except Exception:
            pass


def record_failed_login(conn, ip: str, email: str) -> None:
    """Increments failed attempt count and triggers 5-minute lockout if threshold is reached."""
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    row = conn.execute(
        "SELECT attempts FROM login_attempts WHERE ip = ? AND email = ?",
        (ip, email),
    ).fetchone()

    attempts = (row["attempts"] + 1) if row else 1
    locked_until = None
    if attempts >= MAX_FAILED_ATTEMPTS:
        locked_until = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()

    if row:
        conn.execute(
            """
            UPDATE login_attempts
            SET attempts = ?, last_attempt = ?, locked_until = ?
            WHERE ip = ? AND email = ?
            """,
            (attempts, now_str, locked_until, ip, email),
        )
    else:
        conn.execute(
            """
            INSERT INTO login_attempts (ip, email, attempts, last_attempt, locked_until)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ip, email, attempts, now_str, locked_until),
        )
    conn.commit()


def reset_login_attempts(conn, ip: str, email: str) -> None:
    """Clears failed login counter upon successful authentication."""
    conn.execute("DELETE FROM login_attempts WHERE ip = ? AND email = ?", (ip, email))
    conn.commit()


# --- Session & User Extraction Dependencies ---
def extract_token_from_request(request: Request) -> Optional[str]:
    """Extracts session token from HttpOnly cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip()

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        if bearer_token:
            return bearer_token

    return None


def get_optional_user(
    request: Request,
    db_path: Optional[Union[Path, str]] = None,
) -> Optional[dict]:
    """
    Returns authenticated user dict if session is valid; None otherwise.
    Never raises 401.
    """
    token = extract_token_from_request(request)
    if not token:
        return None

    token_hash = hash_session_token(token)
    now = datetime.now(timezone.utc)

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT s.id AS session_id, s.expires_at,
                   u.id, u.email, u.display_name, u.auto_save_scans, u.created_at, u.updated_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if not row:
            return None

        # Check session expiry
        try:
            exp = datetime.fromisoformat(row["expires_at"])
            if exp <= now:
                # Expired session -> clean up
                conn.execute("DELETE FROM auth_sessions WHERE id = ?", (row["session_id"],))
                conn.commit()
                return None
        except Exception:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "auto_save_scans": bool(row["auto_save_scans"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "session_id": row["session_id"],
        }


def get_current_user(
    user: Optional[dict] = Depends(get_optional_user),
) -> dict:
    """Dependency requiring active user authentication. Raises 401 if unauthenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập hoặc phiên đã hết hạn.",
        )
    return user


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Pydantic Schemas ---
class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    return_to: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str
    return_to: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    auto_save_scans: Optional[bool] = None


def validate_safe_redirect(return_to: Optional[str], default: str = "/account") -> str:
    """
    Validates that return_to is a safe internal relative path.
    Prevents open redirects, protocol-relative URLs (//evil.com), backslashes (/\\evil.com),
    and auth loops back to /auth/login or /auth/register.
    Defaults to '/account'.
    """
    if not return_to or not isinstance(return_to, str):
        return default
    target = return_to.strip()
    if not target.startswith("/") or target.startswith("//") or target.startswith("/\\"):
        return default
    path_only = target.split("?")[0]
    if "\\" in path_only or ":" in path_only:
        return default
    lower_path = path_only.lower().rstrip("/")
    if lower_path in {"/auth", "/auth/login", "/auth/register"}:
        return default
    return target


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    """Sets secure HttpOnly session cookie on the response."""
    is_secure = request.url.scheme == "https"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
        secure=is_secure,
    )



# --- Router Endpoints ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    db_path: Optional[Union[Path, str]] = None,
):
    """Registers a new user account, creates session, and sets auth cookie."""
    email_clean = req.email.strip().lower()
    if not EMAIL_REGEX.match(email_clean):
        raise HTTPException(status_code=400, detail="Email không đúng định dạng.")
    name_clean = req.display_name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Tên hiển thị không được để trống.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự.")

    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    user_id = uuid.uuid4().hex
    pwd_hash = hash_password(req.password)

    with get_db_connection(db_path) as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email_clean,)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã được sử dụng.")

        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, display_name, auto_save_scans, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (user_id, email_clean, pwd_hash, name_clean, now_str, now_str),
        )

        # Create session
        token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(token)
        session_id = uuid.uuid4().hex
        expires_at = (now + timedelta(seconds=SESSION_MAX_AGE_SECONDS)).isoformat()

        conn.execute(
            """
            INSERT INTO auth_sessions (id, user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_id, token_hash, now_str, expires_at),
        )
        conn.commit()

    set_session_cookie(response, request, token)
    safe_return_to = validate_safe_redirect(req.return_to or request.query_params.get("return_to"))

    return {
        "user": {
            "id": user_id,
            "email": email_clean,
            "display_name": name_clean,
            "auto_save_scans": True,
            "created_at": now_str,
        },
        "return_to": safe_return_to,
        "redirect_to": safe_return_to,
    }


@router.post("/login")
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db_path: Optional[Union[Path, str]] = None,
):
    """Authenticates user with email/password and rate-limits failed attempts."""
    email_clean = req.email.strip().lower()
    client_ip = request.client.host if request.client else "127.0.0.1"

    with get_db_connection(db_path) as conn:
        check_login_rate_limit(conn, client_ip, email_clean)

        user_row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email_clean,),
        ).fetchone()

        if not user_row or not verify_password(req.password, user_row["password_hash"]):
            record_failed_login(conn, client_ip, email_clean)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác.",
            )

        # Successful login -> reset rate-limit tracking
        reset_login_attempts(conn, client_ip, email_clean)

        # Create session
        token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(token)
        session_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=SESSION_MAX_AGE_SECONDS)).isoformat()

        conn.execute(
            """
            INSERT INTO auth_sessions (id, user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_row["id"], token_hash, now.isoformat(), expires_at),
        )
        conn.commit()

    set_session_cookie(response, request, token)
    safe_return_to = validate_safe_redirect(req.return_to or request.query_params.get("return_to"))

    return {
        "user": {
            "id": user_row["id"],
            "email": user_row["email"],
            "display_name": user_row["display_name"],
            "auto_save_scans": bool(user_row["auto_save_scans"]),
            "created_at": user_row["created_at"],
        },
        "return_to": safe_return_to,
        "redirect_to": safe_return_to,
    }


@router.get("/validate-redirect")
def check_safe_redirect(return_to: Optional[str] = Query(None)):
    """Validates whether a return_to URL is safe for internal redirect."""
    safe_url = validate_safe_redirect(return_to)
    return {"safe_url": safe_url, "return_to": safe_url, "is_safe": safe_url == (return_to or "").strip()}



@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db_path: Optional[Union[Path, str]] = None,
):
    """Destroys current session from database and clears auth cookie."""
    token = extract_token_from_request(request)
    if token:
        token_hash = hash_session_token(token)
        with get_db_connection(db_path) as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
            conn.commit()

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"success": True, "message": "Đã đăng xuất"}


@router.get("/me")
def get_me(user: Optional[dict] = Depends(get_optional_user)):
    """Returns current authenticated user or 200 with user: null if guest."""
    if not user:
        return {"user": None}
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "auto_save_scans": user["auto_save_scans"],
            "created_at": user["created_at"],
        }
    }


@router.patch("/profile")
def update_profile(
    req: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db_path: Optional[Union[Path, str]] = None,
):
    """Updates user display_name and/or auto_save_scans preference."""
    updates = []
    params = []

    if req.display_name is not None:
        name_clean = req.display_name.strip()
        if not name_clean:
            raise HTTPException(status_code=400, detail="Tên hiển thị không được để trống.")
        updates.append("display_name = ?")
        params.append(name_clean)

    if req.auto_save_scans is not None:
        updates.append("auto_save_scans = ?")
        params.append(1 if req.auto_save_scans else 0)

    if not updates:
        return {"user": current_user}

    now_str = datetime.now(timezone.utc).isoformat()
    updates.append("updated_at = ?")
    params.append(now_str)
    params.append(current_user["id"])

    with get_db_connection(db_path) as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

        updated_row = conn.execute(
            "SELECT id, email, display_name, auto_save_scans, created_at, updated_at FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()

    return {
        "user": {
            "id": updated_row["id"],
            "email": updated_row["email"],
            "display_name": updated_row["display_name"],
            "auto_save_scans": bool(updated_row["auto_save_scans"]),
            "created_at": updated_row["created_at"],
            "updated_at": updated_row["updated_at"],
        }
    }
