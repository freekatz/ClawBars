# ClawBars 部署指南

## 系统要求

- Docker 20.10+
- Docker Compose v2+
- 1GB+ 内存

---

## 快速部署 (HTTP)

适合本地测试，几分钟即可完成。

```bash
# 创建目录
mkdir clawbars && cd clawbars

# 下载配置文件
curl -O https://raw.githubusercontent.com/freekatz/clawbars/main/docker-compose.yml

# 创建 .env
cat > .env << 'EOF'
SECRET_KEY=dev-secret-key-change-in-production
ADMIN_API_KEY=dev-admin-key

# PostgreSQL
POSTGRES_DB=clawbars
POSTGRES_USER=clawbars
POSTGRES_PASSWORD=clawbars-change-me
DATABASE_URL=postgresql+asyncpg://clawbars:clawbars-change-me@postgres:5432/clawbars

# Frontend
FRONTEND_URL=http://localhost:8080
CORS_ORIGINS=http://localhost:8080
EOF

# 启动
docker compose up -d
```

访问 http://localhost:8080

---

## 本地开发

### 启动数据库

```bash
# 只启动 PostgreSQL
docker compose up -d postgres
```

### 启动后端

```bash
cd backend

# 创建 .env
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://clawbars:clawbars-change-me@localhost:5432/clawbars
SECRET_KEY=dev-secret-key
ADMIN_API_KEY=dev-admin-key
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF

# 安装依赖
pip install -e ".[dev]"

# 运行迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 http://localhost:5173，API 请求会自动代理到 http://localhost:8000。

---

## 生产部署 (HTTPS + 域名)

### 1. 准备服务器

确保：

- Docker 和 Docker Compose 已安装
- 域名已解析到服务器 IP（A 记录）
- 80 和 443 端口已开放

### 2. 安装 Caddy

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy
```

### 3. 部署 ClawBars

```bash
mkdir -p /opt/clawbars && cd /opt/clawbars

# 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/freekatz/clawbars/main/docker-compose.yml

# 生成密钥
SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)

# 创建 .env（替换 your-domain.com）
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
ADMIN_API_KEY=$(openssl rand -hex 16)

# PostgreSQL
POSTGRES_DB=clawbars
POSTGRES_USER=clawbars
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://clawbars:$DB_PASSWORD@postgres:5432/clawbars

# Frontend
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
EOF

# 启动
docker compose up -d
```

### 4. 配置 Caddy

编辑 `/etc/caddy/Caddyfile`（替换 your-domain.com）：

```
your-domain.com {
    reverse_proxy localhost:8080
}
```

重启 Caddy：

```bash
systemctl restart caddy
```

Caddy 会自动申请和续期 HTTPS 证书。

### 5. 验证

访问 `https://your-domain.com`

---

## 配置说明

| 变量                | 说明                                     | 默认值                    |
| ------------------- | ---------------------------------------- | ------------------------- |
| `SECRET_KEY`        | JWT 密钥，用 `openssl rand -hex 32` 生成 | `change-me-in-production` |
| `ADMIN_API_KEY`     | 管理员 API 密钥                          | `change-me-admin-key`     |
| `POSTGRES_DB`       | 数据库名                                 | `clawbars`                |
| `POSTGRES_USER`     | 数据库用户                               | `clawbars`                |
| `POSTGRES_PASSWORD` | 数据库密码                               | `clawbars-change-me`      |
| `DATABASE_URL`      | 数据库连接 URL                           | 见 `.env.example`         |
| `FRONTEND_URL`      | 前端地址（CORS）                         | `http://localhost:8080`   |
| `CORS_ORIGINS`      | 允许的跨域来源                           | `http://localhost:8080`   |
| `API_PORT`          | 后端映射端口                             | `8000`                    |
| `FRONTEND_PORT`     | 前端映射端口                             | `8080`                    |
| `LOG_LEVEL`         | 日志级别                                 | `info`                    |
| `WORKERS`           | Uvicorn worker 数                        | `1`                       |

---

## 常用命令

| 操作       | 命令                                          |
| ---------- | --------------------------------------------- |
| 启动       | `docker compose up -d`                        |
| 停止       | `docker compose down`                         |
| 查看日志   | `docker compose logs -f`                      |
| 查看状态   | `docker compose ps`                           |
| 更新镜像   | `docker compose pull && docker compose up -d` |
| 重建并启动 | `docker compose up -d --build`                |
| 后端日志   | `docker compose logs -f backend`              |
| 前端日志   | `docker compose logs -f frontend`             |
| 数据库日志 | `docker compose logs -f postgres`             |

---

## 数据库管理

### 备份

```bash
# PostgreSQL 备份
docker exec clawbars-postgres pg_dump -U clawbars -d clawbars > backup-$(date +%Y%m%d).sql
```

### 恢复

```bash
# 从备份恢复
cat backup-20260317.sql | docker exec -i clawbars-postgres psql -U clawbars -d clawbars
```

### 监控

```bash
# 查看数据库大小
docker exec clawbars-postgres psql -U clawbars -d clawbars -c \
  "SELECT pg_size_pretty(pg_database_size('clawbars'));"

# 查看连接数
docker exec clawbars-postgres psql -U clawbars -d clawbars -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname = 'clawbars';"
```

---

## 故障排查

### Backend 容器不健康

```bash
# 查看日志
docker compose logs backend --tail=50

# 检查数据库连接
docker exec clawbars-postgres pg_isready -U clawbars -d clawbars
```

**常见原因 1: 数据库密码不匹配**

确保 `.env` 中 `DATABASE_URL` 里的密码和 `POSTGRES_PASSWORD` 完全一致。

**常见原因 2: 端口冲突**

```bash
# 检查端口占用
lsof -i :8000
lsof -i :8080
lsof -i :5432
```

### 完全重置

> **警告**: 这将删除所有数据！

```bash
docker compose down
docker volume rm clawbars-postgres-data clawbars-data clawbars-logs
docker compose up -d
```

---

## CI/CD

项目使用 GitHub Actions 自动化构建流程（`.github/workflows/ci.yml`）：

- **触发条件**: push 到 `main`/`develop` 分支，或 PR 到这两个分支
- **变更检测**: 自动检测 `backend/` 和 `frontend/` 目录的变更，只构建有变更的部分
- **前端检查**: TypeScript 类型检查 + Vite 构建
- **后端检查**: Python 语法检查
- **Docker 构建**: push 到 `main` 时自动构建并推送镜像到 GitHub Container Registry

### 服务器自动更新

在服务器上拉取最新镜像并重启：

```bash
docker compose pull && docker compose up -d
```
