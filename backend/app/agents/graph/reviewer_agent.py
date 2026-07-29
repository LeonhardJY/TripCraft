"""Reviewer Agent — 真 LLM 质量审查。

独立调用 LLM 对生成的行程进行质量评判，
给出 pass/fail 判定和具体的改进建议。
"""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.agents.graph.state import TripState
from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
)
from app.services.weather_service import get_weather_forecast

logger = logging.getLogger(__name__)

REVIEWER_SYSTEM_PROMPT = """你是一个旅行规划质检专家。你负责审核 AI 生成的行程方案质量。

审核标准：
1. 完整性 —— 每天是否有景点、餐饮、住宿安排？行程天数是否与用户要求一致？
2. 合理性 —— 路线是否通顺（不出现"今天在北京，明天在西安"这种地理跳跃）？节奏是否和用户要求的匹配？
3. 预算 —— 预算总量是否合理分配到交通/住宿/餐饮/门票？
4. 实用性 —— 提示信息是否包含出行建议（天气、着装、错峰）？是否有技术性无意义内容？
5. 用户偏好 —— 是否覆盖了用户标注的偏好标签？

输出 JSON 格式（不要 markdown 包裹）：
{{{{
  "passed": true/false,
  "score": 1-10,
  "issues": ["问题1", "问题2"],
  "suggestions": ["改进建议1", "改进建议2"],
  "strengths": ["做得好的地方"]
}}}}

注意：passed=false 只有在行程有重大缺陷时才判。小问题可以通过 suggestions 指出，仍然 passed=true。
"""


class ReviewVerdict(BaseModel):
    """Reviewer Agent 的结构化判决。"""
    passed: bool
    score: int = Field(..., ge=1, le=10)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)


TECH_KEYWORDS = ("LLM", "RAG", "LangChain", "Chroma", "演示", "测试", "模型", "源码")


def _build_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.2,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def reviewer_agent(state: TripState) -> dict:
    """Reviewer Agent：LLM 独立判断行程质量。"""
    raw = state.get("planner_raw")
    if not raw:
        return {
            "review_passed": False,
            "review_feedback": ["行程数据为空，无法审核。"],
            "enriched_itinerary": None,
        }

    # 1. LLM 质量审查
    llm = _build_llm()
    llm_passed = True
    feedback: list[str] = []
    suggestions: list[str] = []

    if llm:
        try:
            input_json = json.dumps(raw, ensure_ascii=False, indent=2)
            # 控制输入长度，避免 token 浪费
            if len(input_json) > 8000:
                input_json = input_json[:8000] + "\n... (truncated)"

            response = llm.invoke([
                ("system", REVIEWER_SYSTEM_PROMPT),
                ("human", f"用户偏好: {state.get('preferences', [])}\n"
                          f"节奏: {state.get('pace', '未指定')}\n"
                          f"预算: {state.get('budget', 0)}\n\n"
                          f"生成的行程:\n{input_json}"),
            ])
            raw_out = response.content.strip()
            if raw_out.startswith("```"):
                raw_out = raw_out.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            verdict = json.loads(raw_out)

            logger.info(
                "[ReviewerAgent·LLM] score=%d/10 passed=%s issues=%d",
                verdict.get("score", 0), verdict.get("passed", False),
                len(verdict.get("issues", [])),
            )

            llm_passed = verdict.get("passed", True)
            feedback = verdict.get("issues", [])
            suggestions = verdict.get("suggestions", [])

        except Exception as exc:
            logger.warning("[ReviewerAgent] LLM review failed: %s", exc)
            # fallthrough: LLM 失败不影响最终输出
    else:
        logger.info("[ReviewerAgent] LLM unavailable, skipping AI review")

    # 2. 规则级过滤技术性提示
    raw_tips = raw.get("tips", [])
    clean_tips = [
        t for t in raw_tips
        if not any(kw in t for kw in TECH_KEYWORDS)
    ]
    if not clean_tips:
        destination = state.get("normalized_destination") or raw.get("destination", "目的地")
        clean_tips = [
            f"建议根据{destination}当天天气准备雨具或薄外套。",
            "热门景点建议错峰出发。",
        ]

    # 3. 天气补充提示
    try:
        city = state.get("normalized_destination") or raw.get("destination", "")
        weather = get_weather_forecast(city)
        if weather and weather.get("days"):
            txt = " ".join(
                f"{d.get('day_weather', '')}{d.get('night_weather', '')}"
                for d in weather["days"]
            )
            if any(k in txt for k in ("雨", "阵雨", "雷阵雨")):
                clean_tips.append("天气可能有雨，建议随身带伞。")
    except Exception as exc:
        logger.warning("[ReviewerAgent] weather check failed: %s", exc)

    # 4. 组装最终行程
    enriched = dict(raw)
    enriched["tips"] = clean_tips
    enriched["source_notes"] = [
        "路线基于本地攻略知识库生成，地图信息由高德服务补充。"
    ]

    return {
        "enriched_itinerary": enriched,
        "review_passed": llm_passed,
        "review_feedback": feedback + suggestions if not llm_passed else [],
    }


def reviewer_should_retry(state: TripState) -> str:
    if state.get("review_passed", False):
        return "end"
    retry = state.get("retry_count", 0)
    if retry < state.get("max_retries", 1):
        return "planner"
    return "end"
