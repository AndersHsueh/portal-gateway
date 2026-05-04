import os

# 数据库 - 放在 backend 同级的 data 目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(BASE_DIR), 'data', 'portal.db')}"

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production-2026"  # 生产环境需要更复杂的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 14  # 2周有效期

# 项目列表 JSON
PROJECT_LIST_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "project-list.json")