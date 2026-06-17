import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
JWT_SECRET: str = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12

BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")

_cfg_path = Path(__file__).parent.parent / "config" / "default.json"
with open(_cfg_path) as _f:
    APP_CONFIG: dict = json.load(_f)
