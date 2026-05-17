import os

# 数据库 - 放在 backend 同级的 data 目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(os.path.dirname(BASE_DIR), 'data', 'portal.db')}")

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production-2026"  # 生产环境需要更复杂的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 14  # 2周有效期

# 项目列表 JSON
PROJECT_LIST_PATH = os.environ.get("PROJECT_LIST_PATH", os.path.join(os.path.dirname(BASE_DIR), "data", "project-list.json"))

# SMTP 邮件配置
SMTP_HOST = "smtp.126.com"
SMTP_PORT = 465
SMTP_USER = "a_ni_xue@126.com"
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "FJ53Bf5ecUdxbFcZ")
SMTP_FROM = f"老薛的技术博客 <{SMTP_USER}>"

# K8s Dashboard 认证配置
K8S_DASHBOARD_TOKEN = os.environ.get("K8S_DASHBOARD_TOKEN", "")
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", ".aliceintelligence.work")