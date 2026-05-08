# AI HR · 智能面试工作台

一个轻量的 AI HR 助手 Web 应用，以 **表格（Spreadsheet）** 的形式同时处理多位候选人，每一行从左到右完成一次完整的面试闭环。

> 想把它部署成网站给朋友一起用？请看 [DEPLOY.md](./DEPLOY.md)。

## 能力

| # | ① 岗位需求 JD | ② 候选人简历 | ③ 关注事项 | ④ AI 生成面试问题 | ⑤ 面试记录 | ⑥ AI 分析 · 打分 |
|---|----|----|----|----|----|----|

- **多行候选人并行**：每行独立维护 JD、简历、关注事项、面试问题、记录和分析结果。
- **批量导入简历**：一次可上传多份 PDF / DOCX / TXT，每份自动生成一行。
- **AI 生成面试提纲**：结合 JD + 简历 + 关注事项，输出结构化问题、考察目的、评分要点。
- **AI 面试记录复盘**：返回多维度评分、优劣势、风险、追问建议、综合打分与推荐结论。
- **零数据库**：数据落地到本地 JSON 文件；上传的简历原文保留在 `uploads/` 目录下。

## 多用户支持

本应用内置了完整的用户系统：

- 用户名 + 密码登录，PBKDF2 加盐哈希
- 邀请码注册：不开放匿名注册，只有你分发的邀请码才能创建账号
- 管理员面板：指定用户登录后顶部会出现「邀请码」按钮，可生成/查看
- 数据完全隔离：每位用户只能看到自己的数据
- Session 有效期 30 天

单机自用时直接 `python -m ai_hr.app`，用启动时环境变量里配置的邀请码注册第一个账号即可。生产部署请看 [DEPLOY.md](./DEPLOY.md)。

## 1. 本地安装

推荐 Python 3.10+。

```bash
cd ai_hr
pip install -r requirements.txt
```

## 2. 配置 LLM API

AI HR 使用 OpenAI 兼容的 `/v1/chat/completions` 接口，你可以接 OpenAI、DeepSeek、通义千问（DashScope OpenAI 兼容模式）、Kimi、本地 Ollama 等。通过环境变量配置：

```bash
# 必填
export AI_HR_API_KEY="sk-xxx"

# 可选（以下是默认值；改成你自己的服务端点/模型名即可）
export AI_HR_API_BASE="https://api.openai.com/v1"
export AI_HR_MODEL="gpt-4o-mini"

# 常见替代示例
# DeepSeek:
#   AI_HR_API_BASE=https://api.deepseek.com/v1   AI_HR_MODEL=deepseek-chat
# 通义千问兼容:
#   AI_HR_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1  AI_HR_MODEL=qwen-plus
# 本地 Ollama:
#   AI_HR_API_BASE=http://localhost:11434/v1     AI_HR_MODEL=qwen2.5:14b
```

## 3. 启动

```bash
# 先设一个 session 密钥（随机字符串即可，避免重启后登录态失效）
export AI_HR_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 注入首批邀请码（至少 1 个，用于注册第一个账号）
export AI_HR_INVITE_CODES="INVITE001,INVITE002"

# 把自己设为管理员（注册后生效）
export AI_HR_ADMIN_USERS="admin"

# 启动
python -m ai_hr.app
```

默认监听 `http://0.0.0.0:8765`。第一次打开会跳到 `/login`，点「注册」，用 `admin` 用户名和 `INVITE001` 创建账号。之后你就是管理员，可以在顶部「邀请码」按钮里生成更多邀请码给朋友。

可通过环境变量自定义：

- `PORT` / `HOST`：监听端口 / 地址
- `AI_HR_UPLOAD_DIR`：简历原文存储目录
- `AI_HR_DATA_FILE`：候选人数据 JSON 文件路径
- `AI_HR_DB_FILE`：用户库（SQLite）路径
- `AI_HR_SECRET_KEY`：session 加密密钥（生产环境必改）
- `AI_HR_INVITE_CODES`：启动时注入的邀请码
- `AI_HR_ADMIN_USERS`：管理员用户名列表（逗号分隔）
- `AI_HR_DISABLE_SIGNUP`：设为 `1` 关闭注册
- `AI_HR_MAX_MB`：单份简历最大大小（默认 16MB）
- `AI_HR_TIMEOUT`：LLM 请求超时秒数（默认 600，Claude Opus 建议 1200）

## 4. 使用流程

1. 点击左上角 **「+ 新增一行候选人」**，或直接把多份简历拖到 **「批量导入简历」** 输入框（可多选）。
2. 在第 ① 列粘贴岗位需求 / JD。
3. 在第 ② 列上传候选人简历（支持 `.pdf / .docx / .txt / .md`），系统会自动解析为纯文本。
4. 在第 ③ 列填入「本次面试想重点考察的点」，例如「考察跨团队协作」「关注近三年的薪资涨幅」「是否能长期出差」等。
5. 点击第 ④ 列的 **「生成面试问题」**，AI 会基于前三列生成：
   - 简历要点速览
   - 重点考察方向
   - 四大类面试问题（含考察目的 + 评分要点）
   - 流程建议 + 风险提示
6. 面试结束后，把对话/纪要粘贴到第 ⑤ 列。
7. 点击第 ⑥ 列的 **「AI 分析 + 打分」**，会得到：
   - 综合得分（0-100）与推荐结论（强烈推荐 / 推荐 / 待定 / 不推荐）
   - 多维度打分（专业能力 / 项目经验 / 沟通表达 / 学习能力 / 稳定性 / 文化匹配 等）
   - 优势、不足/风险、背景核实事项
   - 建议追问的问题
   - 给面试官的复盘建议 & 综合建议

所有修改都会自动保存。

## 5. 目录结构

```
ai_hr/
├── app.py              # Flask 入口 + API
├── config.py           # 环境变量 / 默认配置
├── ai_client.py        # OpenAI 兼容接口客户端
├── prompts.py          # 面试题生成 / 记录分析 Prompt
├── resume_parser.py    # PDF / DOCX / TXT 解析
├── storage.py          # 基于 JSON 文件的持久化
├── requirements.txt
├── templates/
│   └── index.html
├── static/
│   ├── css/app.css
│   └── js/app.js
├── uploads/            # 原始简历文件
└── data/candidates.json
```

## 6. API 速查（可接入自动化）

| Method | Path | 说明 |
|--------|------|------|
| `GET`  | `/api/rows` | 列出所有候选人行 |
| `POST` | `/api/rows` | 新建一行（body 可选 `job_desc` / `focus_points`） |
| `PUT`  | `/api/rows/<id>` | 更新某行字段 |
| `DELETE` | `/api/rows/<id>` | 删除某行 |
| `POST` | `/api/rows/<id>/resume` | 上传并解析简历（form field `file`） |
| `POST` | `/api/rows/bulk_resume` | 批量上传（form field `files[]`，可附 `job_desc` / `focus_points`） |
| `POST` | `/api/rows/<id>/generate_questions` | 生成面试问题 |
| `POST` | `/api/rows/<id>/analyze` | 分析面试记录并打分 |
| `GET`  | `/api/meta` | 当前模型 / API Base / API Key 状态 |

## 7. 服务商兼容性提示

不同 LLM 服务商对 OpenAI 兼容协议的实现差异很大，本应用已经做了多重兜底，但仍有一些实际场景需要注意：

### router.ss.chat / Claude Code 类代理

这类代理是为 **Claude Code 客户端** 设计的，对单次请求大小、参数有严格限制。常见症状：

- 报错 `您的请求携带的一些参数似乎不正确，可能原则于...上下文过长`
- HTTP 400 / 422 频繁出现

应用已经做了**自动重试缩短上下文**（默认 → 2000 → 800 字符/字段），如果仍失败：

```bash
# 进一步压缩单字段长度
export AI_HR_MAX_FIELD_CHARS=1500
```

或者换一家代理：

| 推荐服务商 | API_BASE | 备注 |
|------|------|------|
| DeepSeek 官方 | `https://api.deepseek.com/v1` | 性价比高，速度快，对长上下文友好 |
| OpenRouter | `https://openrouter.ai/api/v1` | 一个 Key 调全家桶，含 Claude / GPT / Llama 等 |
| Kimi | `https://api.moonshot.cn/v1` | 国产，长上下文专长 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 国产，价格友好 |
| 火山方舟（豆包） | `https://ark.cn-beijing.volces.com/api/v3` | 国产，速度快 |

### Claude 模型对 JSON 格式遵从一般

应用已经做了 **JSON 自动修复重试**，但首次成功率会比 GPT-4o / Sonnet 低。如果你主要做 ⑥ AI 分析+打分，推荐用：

- `gpt-4o-mini`（性价比首选）
- `claude-3-5-sonnet-20241022`（质量+JSON 都好）
- `deepseek-chat`（国产首选）

## 8. 常见报错排查

### ① `解析 LLM 响应失败 ... 原文: <!doctype html>...`

LLM 接口返回的是 HTML 页面而不是 JSON，**几乎一定是 `AI_HR_API_BASE` 配错了**（路径不对、少了 `/v1`、域名错）。

- 页面右上角点 **「连通性自检」** 按钮，或直接访问 `http://localhost:8765/api/diagnose` 查看详细错误。
- 正确的 base URL：
  - OpenAI 官方：`https://api.openai.com/v1`
  - DeepSeek：`https://api.deepseek.com/v1`
  - 通义千问兼容模式：`https://dashscope.aliyuncs.com/compatible-mode/v1`
  - Kimi：`https://api.moonshot.cn/v1`
  - 火山方舟（豆包）：`https://ark.cn-beijing.volces.com/api/v3`
  - router.ss.chat / oneapi 之类的聚合代理：**通常要带 `/v1`**，请看服务商文档
  - 本地 Ollama：`http://localhost:11434/v1`
- 用 curl 最快验证：
  ```bash
  curl -sS -X POST "$AI_HR_API_BASE/chat/completions" \
    -H "Authorization: Bearer $AI_HR_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$AI_HR_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":20}"
  ```
  看到 `{"choices":[{...}]}` 即配置正确；看到 `<html>` 说明 base 错；看到 `{"error":...}` 按错误信息处理。

### ② 上传 PDF 偶尔解析失败

- 已内置两套解析器：先用 `pdfminer.six`，失败再用 `pypdf` 兜底。
- 扫描版 PDF（整页都是图片）任何非 OCR 解析都会失败，请先用 WPS / Adobe 做 OCR，或直接导出为 DOCX / TXT 再上传。
- 加密 PDF 需先移除密码保护。
- 旧版 `.doc` 不支持，另存为 `.docx` 即可。

### ③ 点按钮报 `未设置 AI_HR_API_KEY`

环境变量未在 **启动 Flask 的那个终端** 里设置。重新 `export` 之后再 `python -m ai_hr.app` 启动。

## 9. 安全与隐私

- 所有简历与面试记录均 **仅存储于本地**。若你的部署环境共享，请务必做好访问控制。
- AI 分析会把 JD、简历原文、关注事项、面试记录发送给你配置的 LLM。请在敏感场景下自建本地模型（Ollama / vLLM）。
- 当前示例没有内置鉴权；生产部署建议放在反向代理（Nginx / Caddy）之后并加上 Basic Auth 或 SSO。
