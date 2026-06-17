import hashlib
import hmac
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- Password ---

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# --- JWT ---

def create_access_token(sub: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": sub, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# --- Rate limiter (in-memory sliding window, 5 attempts / 5 min / IP) ---

_attempts: dict[str, list[float]] = defaultdict(list)
_MAX = 5
_WINDOW = 300


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    valid = [t for t in _attempts[ip] if now - t < _WINDOW]
    _attempts[ip] = valid
    if len(valid) >= _MAX:
        return False
    _attempts[ip].append(now)
    return True


# --- Feedback token (HMAC-SHA256, binds paper_id + action + expiry) ---

def gen_feedback_token(paper_id: int, action: str, ttl_hours: int = 72) -> str:
    exp = int(time.time()) + ttl_hours * 3600
    payload = f"{paper_id}:{action}:{exp}"
    sig = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{paper_id}:{action}:{exp}:{sig}"


def verify_feedback_token(token: str) -> Optional[tuple[int, str]]:
    try:
        paper_id_s, action, exp_s, sig = token.split(":")
        if time.time() > int(exp_s):
            return None
        payload = f"{paper_id_s}:{action}:{exp_s}"
        expected = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        return int(paper_id_s), action
    except Exception:
        return None
