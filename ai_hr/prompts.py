"""AI HR 使用的 prompt 模板。"""
from __future__ import annotations

SYSTEM_HR = (
    "你是一位资深的 HR 与技术面试官，擅长根据岗位需求和候选人简历设计针对性、"
    "可量化的面试问题，并能客观、专业地分析面试记录、给出反馈与评分。"
    "你的回复必须严谨、务实，避免空话套话，并全程使用中文。"
)


def build_questions_messages(job_desc: str, resume_text: str, focus_points: str):
    """生成面试问题 + 考察事项 的 prompt。"""
    user = f"""请根据以下信息，为这位候选人设计一套结构化的面试提纲。

【岗位需求 / JD】
{job_desc or '(未填写)'}

【候选人简历】
{resume_text or '(未提供)'}

【面试官的关注事项】
{focus_points or '(未填写)'}

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
{job_desc or '(未填写)'}

【候选人简历摘要】
{resume_text or '(未提供)'}

【面试官的关注事项】
{focus_points or '(未填写)'}

【事先生成的面试问题与考察事项】
{interview_questions or '(未提供)'}

【本次的面试记录 / 纪要】
{interview_notes or '(未提供)'}

请严格以 **JSON 对象** 形式返回，不要包含 JSON 以外的任何内容。结构如下：
{{
  "overall_score": 0-100 的整数,
  "recommendation": "strong_hire | hire | hold | no_hire",
  "recommendation_label": "强烈推荐 / 推荐 / 待定 / 不推荐 中选一个",
  "fit_summary": "一句话总结候选人与该岗位的匹配度",
  "dimensions": [
    {{"name": "维度名称，如 专业能力 / 项目经验 / 沟通表达 / 学习能力 / 稳定性 / 文化匹配 等",
      "score": 0-100,
      "comment": "该维度的详细点评，结合面试记录中的具体证据" }}
  ],
  "strengths": ["优势 1", "优势 2", "..."],
  "concerns": ["不足或风险 1", "不足或风险 2", "..."],
  "follow_up_questions": ["如需二面/加面，建议追问的问题 1", "..."],
  "background_check": ["建议背景核实的事项 1", "..."],
  "feedback_to_interviewer": "给面试官本人的复盘建议（如提问方式、漏问点等）",
  "final_advice": "综合建议：是否进入下一轮 / 是否发 offer / 薪资建议区间等"
}}

打分准则：
- overall_score >= 85：强烈推荐；70-84：推荐；55-69：待定；<55：不推荐。
- dimensions 至少包含 5 个维度；若某维度因记录缺失无法判断，请在 comment 中明确指出"证据不足"。
- 所有文字字段使用中文。
"""
    return [
        {"role": "system", "content": SYSTEM_HR},
        {"role": "user", "content": user},
    ]
