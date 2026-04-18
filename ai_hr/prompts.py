"""AI HR 使用的 prompt 模板。"""
from __future__ import annotations

# 简历/面试记录往往很长，这里统一做一个软性截断，避免 prompt 过长导致超时或成本飙升。
MAX_FIELD_CHARS = 12000


def _clip(text: str, n: int = MAX_FIELD_CHARS) -> str:
    if not text:
        return text
    if len(text) <= n:
        return text
    return text[:n] + f"\n...(超出 {len(text) - n} 字已截断)..."


SYSTEM_HR = (
    "你是一位资深的 HR 与技术面试官，擅长根据岗位需求和候选人简历设计针对性、"
    "可量化的面试问题，并能客观、专业地分析面试记录、给出反馈与评分。"
    "你的回复必须严谨、务实，避免空话套话，并全程使用中文。"
)

SYSTEM_HR_JSON = (
    "你是一位资深的 HR 与技术面试官。你的输出必须是**一个合法的 JSON 对象**，"
    "不要使用 Markdown 代码块包裹，不要在 JSON 前后加任何解释性文字、前缀、后缀，"
    "直接以 '{' 开头、以 '}' 结尾。字段内部使用中文。"
)


def build_questions_messages(job_desc: str, resume_text: str, focus_points: str):
    """生成面试问题 + 考察事项 的 prompt。"""
    user = f"""请根据以下信息，为这位候选人设计一套结构化的面试提纲。

【岗位需求 / JD】
{_clip(job_desc) or '(未填写)'}

【候选人简历】
{_clip(resume_text) or '(未提供)'}

【面试官的关注事项】
{_clip(focus_points) or '(未填写)'}

请按以下结构输出，使用 Markdown 分级标题与列表：
1. **简历要点速览**：3-6 条，总结候选人的核心背景与亮点/疑点。
2. **本次面试要着重考察的方向**：结合 JD 与关注事项，列出 3-6 个考察维度，并说明理由。
3. **面试问题清单**：分为「项目/经验类」「专业/技术类」「行为/软技能类」「针对关注事项的追问」四组，
   每组 3-6 题。每题给出：
   - 问题正文
   - 考察目的
   - 期望答案要点 / 评分要点（bullet 列表）
4. **面试流程建议**：时间分配、需要实操/编码/案例的环节、拟邀请的面试官角色。
5. **风险提示与背景调查要点**：基于简历中的潜在风险点提示。
"""
    return [
        {"role": "system", "content": SYSTEM_HR},
        {"role": "user", "content": user},
    ]


def build_analysis_messages(
    job_desc: str,
    resume_text: str,
    focus_points: str,
    interview_questions: str,
    interview_notes: str,
):
    """分析面试记录并给出反馈 + 打分 的 prompt。要求 JSON 输出。"""
    user = f"""请基于以下材料，对本次面试进行专业分析，并给出结构化评分与建议。

【岗位需求 / JD】
{_clip(job_desc) or '(未填写)'}

【候选人简历摘要】
{_clip(resume_text) or '(未提供)'}

【面试官的关注事项】
{_clip(focus_points) or '(未填写)'}

【事先生成的面试问题与考察事项】
{_clip(interview_questions) or '(未提供)'}

【本次的面试记录 / 纪要】
{_clip(interview_notes) or '(未提供)'}

**评分原则（非常重要，必须严格遵守）**：
- 评分只基于两件事：
  (A) **简历与 JD 的匹配度**：候选人过往背景 / 项目 / 技能是否契合本岗位要求；
  (B) **面试问答表现**：回答的正确性、深度、逻辑性、是否扣题、是否有具体证据。
- **不要**评判文化匹配 / 稳定性 / 学习能力 / 性格 / 职业发展 等任何无法从简历 + 面试记录中直接得出证据的维度。
- 每一条打分、每一条点评都必须能对应到"简历原文 / JD 条款 / 面试记录中的某句回答"作为证据。
  点评中尽量用"候选人在回答 XX 问题时提到 YY"、"简历里写了 ZZ、对应 JD 的 WW 要求"这种句式。
- 若面试记录未覆盖某个 JD 要求，请在 comment 里写"面试未考察到，证据不足"，不要猜测打分。

请严格以 **JSON 对象** 形式返回，不要包含 JSON 以外的任何内容。结构如下：
{{
  "overall_score": 0-100 的整数,
  "recommendation": "strong_hire | hire | hold | no_hire",
  "recommendation_label": "强烈推荐 / 推荐 / 待定 / 不推荐 中选一个",
  "fit_summary": "一句话总结：简历与 JD 的匹配度 + 面试整体表现",

  "resume_jd_match": {{
    "score": 0-100 的整数,
    "matched": ["简历/经历中明确满足 JD 的要点 1（附 JD 对应条款）", "要点 2", "..."],
    "gaps": ["简历中缺失或明显不足以覆盖 JD 的要求 1", "要求 2", "..."],
    "comment": "对简历-JD 匹配度的整体点评，必须引用简历原文 / JD 原文作为证据"
  }},

  "interview_performance": {{
    "score": 0-100 的整数,
    "question_reviews": [
      {{
        "question": "面试官提出的问题原文 / 核心意思",
        "answer_summary": "候选人回答要点摘要（基于面试记录）",
        "evaluation": "对这道题回答的具体评价：是否扣题、是否有深度、是否有具体例子 / 数据支撑",
        "score": 0-100 的整数
      }}
    ],
    "comment": "对整体面试问答表现的点评：逻辑性、表达清晰度、回答是否扣题、是否有实例支撑。必须基于面试记录中的具体回答"
  }},

  "strengths": ["简历或面试回答中体现的具体优势 1（附证据）", "优势 2", "..."],
  "concerns": ["简历或面试回答中体现的具体不足/风险 1（附证据）", "不足 2", "..."],
  "follow_up_questions": ["针对本次未讲清楚或需要进一步验证的点，下一轮应追问的问题 1", "..."],
  "final_advice": "综合建议：是否进入下一轮 / 是否发 offer。只基于本次简历+面试，不要推断性格或长期潜力。"
}}

打分准则：
- **overall_score** = 0.5 × resume_jd_match.score + 0.5 × interview_performance.score（四舍五入）。
  若两部分证据差距悬殊，可以在 ±5 以内人工微调，并在 fit_summary 中说明原因。
- overall_score >= 85：强烈推荐；70-84：推荐；55-69：待定；<55：不推荐。
- `question_reviews` 应尽可能覆盖面试记录中每一道问答；若面试记录为空或无法解析，返回空数组并在 comment 中说明。
- 所有文字字段使用中文。

**输出格式硬性要求**：
1. 只输出 JSON 对象，不要有任何解释、前言、结尾。
2. 不要用 ```json ... ``` 代码块包裹。
3. 整段输出必须以 `{{` 开头、以 `}}` 结尾。
4. 字符串里的双引号要转义为 `\\"`；不要使用中文引号。
"""
    return [
        {"role": "system", "content": SYSTEM_HR_JSON},
        {"role": "user", "content": user},
    ]
