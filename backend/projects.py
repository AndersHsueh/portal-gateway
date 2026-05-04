import json
import os
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import PROJECT_LIST_PATH
from database import get_db
from auth import get_current_user
from models import User

router = APIRouter(prefix="/api", tags=["项目"])


def discover_services() -> List[dict]:
    """自动发现服务器上运行的服务"""
    services = []

    # 检查 systemd 服务
    import subprocess
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0].replace(".service", "")
                    # 跳过系统服务
                    if not name.startswith("aa_") and name not in ["nginx", "docker"]:
                        services.append({
                            "name": name.replace("-", " ").replace("_", " ").title(),
                            "description": f"Systemd service: {name}",
                            "icon": "⚙️",
                            "url": f"http://localhost"
                        })
    except:
        pass

    return services


@router.get("/projects")
def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = []

    # 先从 project-list.json 读取
    if os.path.exists(PROJECT_LIST_PATH):
        with open(PROJECT_LIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            projects = data.get("projects", [])

    # 如果没有 JSON 文件，自动发现
    if not projects:
        projects = discover_services()

    return {"projects": projects}