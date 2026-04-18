# AI HR 部署指南（变成一个网站给朋友用）

本文档面向"想把 AI HR 部署成公网站点，邀请朋友一起用"的场景。

系统内置了：

- **用户系统**：用户名 + 密码登录（PBKDF2 加盐哈希）
- **邀请码注册**：不开放匿名注册，只有邀请码才能创建账号，谁都可以被你精确邀请
- **管理员面板**：管理员登录后顶部有「邀请码」按钮，可生成 / 查看邀请码
- **数据隔离**：每位用户只能看到自己上传的 JD / 简历 / 面试记录 / 分析结果
- **生产级服务**：Dockerfile + gunicorn，支持多 worker、30 天 session
- **开关**：`AI_HR_DISABLE_SIGNUP=1` 一键关闭公开注册

## 准备工作

1. 一台公网服务器（1 核 1G 即可），或者任意能运行 Docker 的云平台
2. 一个域名（可选，但推荐，方便 HTTPS）
3. 一份 LLM API Key

## 方式一：VPS + Docker（推荐，最通用）

适合：自己有一台 VPS（腾讯云 / 阿里云 / Vultr / DigitalOcean / Hetzner …）

### 1. 安装 Docker

```bash
# Debian / Ubuntu
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
```

### 2. 克隆仓库

```bash
cd ~
git clone https://github.com/lsy928256297-ops/stock.git
cd stock
git checkout cursor/ai-hr-interview-assistant-387e
cd ai_hr
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env   # 按提示修改
```

必改的字段：

```env
AI_HR_API_KEY=sk-你的Key
AI_HR_API_BASE=https://api.openai.com/v1       # 或者其它兼容服务
AI_HR_MODEL=gpt-4o-mini

# 会话加密密钥，务必改成一串随机字符：
AI_HR_SECRET_KEY=$(openssl rand -hex 32)

# 首批邀请码（后续可在管理员面板增删）
AI_HR_INVITE_CODES=PALFRIEND001,PALFRIEND002,PALFRIEND003

# 管理员用户名（注册后自动获得邀请码管理权限）
AI_HR_ADMIN_USERS=admin
```

### 4. 启动

```bash
docker compose up -d
docker compose logs -f         # 查看启动日志
```

浏览器访问 `http://你的服务器IP:8765`，第一次请使用 `admin` 用户名 + `PALFRIEND001` 邀请码注册，你就是管理员了。之后在页面右上角点「邀请码」生成给朋友的链接。

### 5. 加上域名 + HTTPS（强烈推荐）

最简单的方案：**Caddy** 自动给你签发 Let's Encrypt 证书。

安装 Caddy：

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

把 `/etc/caddy/Caddyfile` 改成：

```
ai-hr.yourdomain.com {
    reverse_proxy 127.0.0.1:8765
}
```

然后把 `ai-hr.yourdomain.com` 的 DNS A 记录指向服务器 IP，再执行：

```bash
sudo systemctl reload caddy
```

同时在 `.env` 里打开 `AI_HR_COOKIE_SECURE=1` 并重启容器：

```bash
docker compose up -d
```

现在 `https://ai-hr.yourdomain.com` 就是你的 AI HR 网站，自动 HTTPS。

## 方式二：Render（免费 / 不想管服务器）

1. Fork 本仓库到你自己的 GitHub
2. 登录 [Render](https://render.com/) → New → **Web Service** → 连接你的 GitHub
3. 选择仓库和 `cursor/ai-hr-interview-assistant-387e` 分支
4. 设置：
   - **Runtime**: Docker
   - **Dockerfile path**: `ai_hr/Dockerfile`
   - **Docker build context**: `.`（仓库根目录）
   - **Port**: `8765`
5. Environment Variables 里填上 `.env.example` 中列出的所有变量（`AI_HR_API_KEY`、`AI_HR_SECRET_KEY`、`AI_HR_ADMIN_USERS` 等）
6. 点击 Create Web Service，几分钟后 Render 会给你一个 `xxx.onrender.com` 的 HTTPS 域名
7. **建议开启 Persistent Disk** 挂载到 `/app/ai_hr/data` 和 `/app/ai_hr/uploads`，否则重启后数据会丢

## 方式三：Railway

1. [Railway](https://railway.app/) → New Project → Deploy from GitHub
2. 选择仓库 + 分支
3. Railway 会自动识别 Dockerfile。Settings → Root Directory 留空，Dockerfile Path 填 `ai_hr/Dockerfile`
4. Variables 里添加 `.env.example` 中的所有变量
5. 添加一个 **Volume** 挂载到 `/app/ai_hr/data`（持久化用户和候选人数据）
6. Deploy 完成后点击 "Generate Domain" 获取公网地址

## 方式四：Fly.io

```bash
brew install flyctl   # mac
flyctl auth login
cd ai_hr
flyctl launch --no-deploy --dockerfile Dockerfile --copy-config
# 按提示编辑 fly.toml，改 internal_port = 8765

# 设置 secrets
flyctl secrets set AI_HR_API_KEY=sk-xxx AI_HR_SECRET_KEY=$(openssl rand -hex 32) \
    AI_HR_MODEL=gpt-4o-mini AI_HR_ADMIN_USERS=admin \
    AI_HR_INVITE_CODES=PALFRIEND001,PALFRIEND002

# 创建持久卷
flyctl volumes create ai_hr_data --size 1

# 在 fly.toml 里加:
# [mounts]
#   source = "ai_hr_data"
#   destination = "/app/ai_hr/data"

flyctl deploy
```

Fly.io 免费套餐可以跑一个 shared-cpu-1x，256MB 内存够用。

## 朋友怎么用

1. 你在管理员面板生成邀请码，比如 `PALFRIEND999`
2. 发给朋友：访问 `https://ai-hr.yourdomain.com/signup` → 输入用户名、密码、邀请码
3. 登录后，朋友看到的是**只属于他自己的**工作台：他的 JD、他的简历、他的分析结果。谁也看不到别人的。

## 升级与维护

```bash
cd ~/stock/ai_hr
git pull
docker compose up -d --build       # 重新构建并热替换
docker compose logs -f
```

数据存储：

- 用户库：`ai_hr_data` 卷 → `/app/ai_hr/data/users.db`
- 候选人数据：`ai_hr_data` 卷 → `/app/ai_hr/data/candidates.json`
- 简历原文：`ai_hr_uploads` 卷 → `/app/ai_hr/uploads/*`

备份：

```bash
docker run --rm -v ai_hr_data:/data -v $PWD:/backup alpine \
    tar czf /backup/ai_hr_data_$(date +%F).tar.gz -C /data .
```

## 安全提醒

- **`AI_HR_SECRET_KEY` 必须改成你自己的随机值**，不要用默认的 `change-me-...`，否则有人能伪造 session
- 生产环境一定要走 HTTPS，并设 `AI_HR_COOKIE_SECURE=1`
- 定期给系统打补丁：`docker compose pull && docker compose up -d`
- 简历是敏感信息，如果你服务器共享或要合规，建议：
  - 设 `AI_HR_DISABLE_SIGNUP=1` 关闭注册
  - 只用你精确邀请的人
  - 定期清理 `uploads/` 下的原文件（用户侧「删除一行」已经足够）

## 常见问题

**Q：容器起不来，报 `AI_HR_SECRET_KEY` 相关错误**  
A：把 `.env` 里这行改成一串随机字符：`AI_HR_SECRET_KEY=$(openssl rand -hex 32)`

**Q：如何把我当前已经在用的本地数据迁移到服务器？**  
A：本地 `ai_hr/data/candidates.json` 打包上传到服务器 `ai_hr_data` 卷。`docker cp candidates.json ai_hr:/app/ai_hr/data/` 即可。

**Q：想换云厂商 / 服务器，数据怎么办？**  
A：把 `ai_hr_data` 卷 tar 打包迁到新机器解压回去，账号和所有数据都在。

**Q：忘记管理员密码了？**  
A：目前没有做密码找回，最简单的办法：直接编辑数据库。
```bash
docker exec -it ai_hr sh -c "pip install passlib && python - <<'PY'
import sqlite3, hashlib, os
pwd = 'your-new-password'
salt = os.urandom(16)
dk = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt, 260000)
h = f'pbkdf2_sha256\$260000\${salt.hex()}\${dk.hex()}'
c = sqlite3.connect('/app/ai_hr/data/users.db')
c.execute('UPDATE users SET password=? WHERE username=?', (h, 'admin'))
c.commit()
PY"
```
