# AI HR · 智能面试工作台

一个轻量的 AI HR 助手 Web 应用，以 **表格（Spreadsheet）** 的形式同时处理多位候选人，每一行从左到右完成一次完整的面试闭环：

| # | ① 岗位需求 JD | ② 候选人简历 | ③ 关注事项 | ④ AI 生成面试问题 | ⑤ 面试记录 | ⑥ AI 分析 · 打分 |
|---|----|----|----|----|----|----|

- **多行候选人并行**：每行独立维护 JD、简历、关注事项、面试问题、记录和分析结果。
- **批量导入简历**：一次可上传多份 PDF / DOCX / TXT，每份自动生成一行。
- **AI 生成面试提纲**：结合 JD + 简历 + 关注事项，输出结构化问题、考察目的、评分要点。
- **AI 面试记录复盘**：返回多维度评分、优劣势、风险、追问建议、综合打分与推荐结论。
- **零数据库**：数据落地到本地 JSON 文件；上传的简历原文保留在 `uploads/` 目录下。

## 1. 安装

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
# 方式一：模块方式（推荐）
python -m ai_hr.app

# 方式二：直接运行
cd ai_hr && python app.py
```

默认监听 `http://0.0.0.0:8765`。用浏览器打开即可。

可通过环境变量自定义：

- `PORT` / `HOST`：监听端口 / 地址
- `AI_HR_UPLOAD_DIR`：简历原文存储目录
- `AI_HR_DATA_FILE`：候选人数据 JSON 文件路径
- `AI_HR_MAX_MB`：单份简历最大大小（默认 16MB）

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

## 7. 安全与隐私

- 所有简历与面试记录均 **仅存储于本地**。若你的部署环境共享，请务必做好访问控制。
- AI 分析会把 JD、简历原文、关注事项、面试记录发送给你配置的 LLM。请在敏感场景下自建本地模型（Ollama / vLLM）。
- 当前示例没有内置鉴权；生产部署建议放在反向代理（Nginx / Caddy）之后并加上 Basic Auth 或 SSO。
