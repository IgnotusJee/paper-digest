import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
JWT_SECRET: str = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12

ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_EMAIL: str = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD: str = os.environ["ADMIN_PASSWORD"]

BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")

_cfg_path = Path(__file__).parent.parent / "config" / "default.json"
with open(_cfg_path) as _f:
    APP_CONFIG: dict = json.load(_f)
