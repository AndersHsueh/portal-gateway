# OAuth2 风格 CLI 登录方案

## 目标

portal-gateway 作为统一认证中心（SSO），ani（CLI agent）等客户端通过共享 JWT token 实现一次登录、多处使用。

## 流程概览

```
┌──────────┐         ┌──────────────────┐         ┌──────────┐
│  ani CLI │         │ portal-gateway   │         │  浏览器   │
└────┬─────┘         └────────┬─────────┘         └────┬─────┘
     │                        │                        │
     │ 1. 启动，检查本地 token │                        │
     │ 2. 无 token / 已过期    │                        │
     │                        │                        │
     │ 3. 启动 localhost 回调服务 (port=随机)           │
     │ 4. 显示登录 URL ──────────────────────────────→ │
     │                        │                        │
     │                        │ 5. 用户打开 URL，登录   │
     │                        │←───────────────────────│
     │                        │                        │
     │                        │ 6. 登录成功，生成 code  │
     │                        │ 7. 重定向到 localhost   │
     │←── 8. GET /callback?code=xxx ──────────────────│
     │                        │                        │
     │ 9. 用 code 换 token    │                        │
     │──────────────────────→ │                        │
     │←────────────────────── │                        │
     │                        │                        │
     │ 10. 存储 token 到本地  │                        │
     │ 11. 继续运行           │                        │
```

## 详细步骤

### 1. ani 启动 — 检查本地 token

```
~/.ani-auth/token    — JWT access_token
~/.ani-auth/user     — 用户信息 JSON
```

- 读取 token → 调用 `GET /api/auth/me` 验证
- 有效 → 直接运行
- 无效/不存在 → 进入 CLI 登录流程

### 2. CLI 登录流程

#### 2.1 启动本地回调服务

ani 在本地启动一个临时 HTTP 服务，监听随机端口（如 19876）：

```python
# ani 伪代码
port = find_available_port()  # e.g. 19876
state = generate_random_state()  # 防 CSRF
server = start_callback_server(port, state)
```

#### 2.2 显示登录 URL

```
请登录以继续：
  https://aliceintelligence.work/cli-login?redirect_uri=http://localhost:19876/callback&state=a1b2c3

等待登录中...
```

#### 2.3 用户在浏览器登录

portal-gateway 前端展示登录页，登录成功后：

- 后端生成一次性 `code`（短时效，60秒）
- 重定向到 `http://localhost:19876/callback?code=xyz&state=a1b2c3`

#### 2.4 ani 接收回调

```python
# localhost:19876/callback?code=xyz&state=a1b2c3
if query_params["state"] != expected_state:
    return error("state 不匹配")

# 用 code 换 token
token_response = http_post("https://aliceintelligence.work/api/auth/token", {
    "code": query_params["code"],
    "redirect_uri": f"http://localhost:{port}/callback"
})
# → { access_token: "eyJ...", user: { id, email, name, role } }

save_token(token_response)
```

#### 2.5 存储 token

```
~/.ani-auth/
├── token    # JWT access_token 明文
└── user     # { "id": 1, "email": "...", "name": "...", "role": "..." }
```

### 3. Token 共享

多个 CLI 工具可以共享同一个 token 存储位置：

```
~/.portal-auth/
├── token    # JWT access_token
└── user     # 用户信息
```

ani、以及其他 CLI 工具都读写 `~/.portal-auth/`，实现一次登录、全局生效。

## API 设计

### 新增端点

#### `POST /api/auth/cli-login`

发起 CLI 登录，返回登录页 URL 和 state。

**Request:**
```json
{
  "redirect_uri": "http://localhost:19876/callback"
}
```

**Response:**
```json
{
  "login_url": "https://aliceintelligence.work/cli-login?state=a1b2c3&redirect_uri=...",
  "state": "a1b2c3",
  "expires_in": 300
}
```

#### `GET /cli-login`（前端页面）

带 `state` 和 `redirect_uri` 参数的登录页。登录成功后：

1. 后端生成一次性 `code`
2. 重定向到 `{redirect_uri}?code={code}&state={state}`

#### `POST /api/auth/token`

用 code 换 token。

**Request:**
```json
{
  "code": "one-time-code-xyz",
  "redirect_uri": "http://localhost:19876/callback"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "用户名",
    "role": "admin"
  }
}
```

## 数据模型

### AuthorizationCode（一次性授权码）

```python
class AuthCode(Base):
    __tablename__ = "auth_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True)      # 随机生成的一次性 code
    user_id = Column(Integer, ForeignKey("users.id"))    # 关联用户
    redirect_uri = Column(String)                         # 回调地址
    state = Column(String)                                # CSRF 防护
    used = Column(Boolean, default=False)                 # 是否已使用
    expires_at = Column(DateTime)                         # 过期时间（60秒）
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 安全考虑

| 风险 | 对策 |
|------|------|
| CSRF 攻击 | state 参数随机生成，回调时校验 |
| code 被截获 | code 60秒过期 + 一次性使用 |
| redirect_uri 劫持 | 只允许 `http://localhost:*` 的回调地址 |
| token 泄露 | 本地文件权限 600，JWT 有效期 14 天 |
| 暴力猜 code | code 长度 32 字节随机 hex |

## 实现清单

### portal-gateway 改动

- [ ] `backend/models.py` — 新增 `AuthCode` 模型
- [ ] `backend/auth.py` — 新增 `/api/auth/cli-login`、`/api/auth/token` 端点
- [ ] `frontend/index.html` — 新增 CLI 登录页面（识别 `state` 参数，登录后重定向）
- [ ] 数据库迁移 — 创建 `auth_codes` 表

### ani 改动

- [ ] 启动时检查 `~/.portal-auth/token`
- [ ] 验证 token（调 `/api/auth/me`）
- [ ] 无效时启动 localhost 回调服务
- [ ] 显示登录 URL，等待回调
- [ ] 用 code 换 token，存储到本地
- [ ] 登录成功后继续运行
