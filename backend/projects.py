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


def get_port_from_url(url: str) -> int | None:
    """从 URL 中提取端口号"""
    if not url:
        return None
    if ":" in url:
        try:
            return int(url.rsplit(":", 1)[1].strip("/"))
        except ValueError:
            return None
    return None


def merge_projects(json_projects: List[dict], discovered: List[dict]) -> List[dict]:
    """合并 JSON 配置和自动发现的服务，JSON 优先"""
    # 构建结果：先加入所有 JSON 项目
    result = list(json_projects)
    result_ids = {p.get("id") for p in json_projects}
    result_ports = {get_port_from_url(p.get("url", "")) for p in json_projects}

    # 用端口号做 key，构建 discovered 字典
    discovered_by_port = {}
    for s in discovered:
        port = get_port_from_url(s.get("url", ""))
        if port:
            discovered_by_port[port] = s

    # 如果 discovered 的端口不在 JSON 中，补充缺失字段后加入结果
    for p in result:
        port = get_port_from_url(p.get("url", ""))
        if port and port in discovered_by_port:
            d = discovered_by_port[port]
            if not p.get("description"):
                p["description"] = d.get("description", "")
            if not p.get("icon"):
                p["icon"] = d.get("icon", "⚙️")

    # discovered 中有但 JSON 中没有的服务（按端口去重），也加入结果
    for d in discovered:
        d_port = get_port_from_url(d.get("url", ""))
        if d_port and d_port not in result_ports:
            result.append(d)
            result_ports.add(d_port)

    return result


def get_all_running_services() -> List[dict]:
    """获取所有正在监听的 TCP 服务（排除系统端口）"""
    services = []
    import subprocess

    # 扫描所有 listening port
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            # 跳过表头
            if "Local Address" in line or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                addr = parts[3]  # e.g. 0.0.0.0:17573
                if ":" in addr:
                    port_str = addr.rsplit(":", 1)[1]
                    try:
                        port = int(port_str)
                    except ValueError:
                        continue
                    # 排除常见系统端口
                    if port > 10000:
                        services.append({
                            "port": port,
                            "name": f"Service on port {port}",
                            "description": f"运行在端口 {port}",
                            "icon": "⚙️",
                            "url": f"http://101.201.32.200:{port}"
                        })
    except:
        pass

    # 检查 systemd 服务
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
                    if not name.startswith("aa_") and name not in ["nginx", "docker"]:
                        services.append({
                            "port": None,
                            "name": name.replace("-", " ").replace("_", " ").title(),
                            "description": f"Systemd service: {name}",
                            "icon": "⚙️",
                            "url": None
                        })
    except:
        pass

    return services


@router.get("/projects")
def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    json_projects = []
    all_projects = []

    # 1. 从 project-list.json 读取
    if os.path.exists(PROJECT_LIST_PATH):
        with open(PROJECT_LIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            json_projects = data.get("projects", [])

    # 2. 自动发现运行中的服务
    discovered = get_all_running_services()

    # 3. JSON 配置优先，缺失字段用自动发现补充
    all_projects = merge_projects(json_projects, discovered)

    # 4. 如果 JSON 为空且没有自动发现结果，返回默认提示
    if not all_projects:
        all_projects = discovered

    return {"projects": all_projects}