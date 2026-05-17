# Anders' TechBlog - 老薛的技术博客

企业级服务门户，支持邮箱登录、JWT认证、服务卡片展示和管理员用户管理。

## 功能特性

- **邮箱登录** - JWT 认证，2周有效期
- **注册/忘记密码** - 邮箱验证码自助注册和重置密码
- **服务卡片** - 显示项目名称和描述（不暴露端口）
- **管理员功能** - 用户 CRUD、登录日志
- **自动发现** - 支持 systemd 服务自动发现
- **Docker 部署** - 一键 docker-compose 部署

## 技术栈

- **前端**: 原生 HTML/CSS/JS，单页应用
- **后端**: FastAPI + SQLAlchemy + SQLite
- **认证**: JWT (python-jose) + bcrypt
- **邮件**: aiosmtplib (126邮箱 SMTP)
- **部署**: Docker + Nginx

## 快速开始

### Docker 部署（推荐）

```bash
docker-compose up --build -d
```

访问 http://localhost 即可使用。

停止服务：

```bash
docker-compose down
```

### 手动部署

#### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8890
```

#### 前端

直接用 nginx 托管 `frontend/index.html`，反向代理 `/api/` 到后端。

#### Nginx 配置

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root /home/anders/portal-gateway/frontend;
        index index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8890/api/;
    }
}
```

## 默认管理员

- 邮箱: `anderssitvosinvallage@tutamail.com`
- 密码: `1223`

## 目录结构

```
portal-gateway/
├── docker-compose.yml       # Docker 编排
├── frontend/
│   ├── index.html           # 单页应用（登录+注册+仪表盘+管理）
│   ├── nginx.conf           # Nginx 配置
│   └── Dockerfile           # 前端 Docker 镜像
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── auth.py              # 认证路由（登录/注册/验证码/重置密码）
│   ├── email_service.py     # 邮件发送服务
│   ├── users.py             # 用户管理
│   ├── projects.py          # 项目列表
│   ├── models.py            # SQLAlchemy 模型
│   ├── database.py          # 数据库连接
│   ├── config.py            # 配置（支持环境变量）
│   ├── requirements.txt
│   └── Dockerfile           # 后端 Docker 镜像
└── data/
    ├── portal.db            # SQLite 数据库
    └── project-list.json    # 服务列表配置
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite:///../data/portal.db` |
| `PROJECT_LIST_PATH` | 项目列表 JSON 路径 | `../data/project-list.json` |
| `SMTP_PASSWORD` | 邮箱 SMTP 授权码 | 内置默认值 |

## API 端点

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前用户 |
| POST | `/api/auth/send-code` | 发送验证码 |
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/reset-password` | 重置密码 |
| GET | `/api/projects` | 服务列表 |
| GET | `/api/admin/users` | 用户列表（Admin） |
| POST | `/api/admin/users` | 创建用户 |
| PUT | `/api/admin/users/{id}` | 更新用户 |
| DELETE | `/api/admin/users/{id}` | 删除用户 |
| POST | `/api/admin/users/{id}/reset-password` | 重置密码 |
| GET | `/api/admin/logs` | 登录日志 |
