"""Reviewer Agent — LLM 质量审查 + 向 Planner 发送反馈。"""

from __future__ import annotations

import datetime
import json
import logging

from langchain_openai import ChatOpenAI

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

REVIEWER_SYSTEM_PROMPT = """你是一个旅行规划质检专家。审核 AI 生成的行程方案。

审核标准：
1. 完整性 — 每天是否有景点、餐饮、住宿？天数是否匹配？
2. 合理性 — 路线是否有地理跳跃？节奏是否匹配用户偏好？
3. 预算 — 分配是否合理？
4. 偏好覆盖 — 是否包含用户标注的偏好？
5. 实用性 — 提示是否包含有用建议？

如果是修正后的版本（second_review=true），请检查修正是否解决了之前的问题。

输出 JSON（不要 markdown）：
{{"passed": true/false, "score": 1-10, "issues": ["问题1"], "suggestions": ["建议1"],
  "strengths": ["亮点1"], "requires_revision": true/false}}
"""

TECH_KEYWORDS = ("LLM", "RAG", "LangChain", "Chroma", "演示", "测试", "模型", "源码")


def _build_llm():
    return ChatOpenAI(
        model=LLM_MODEL, temperature=0.2,
        api_key=LLM_API_KEY, base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS, max_retries=LLM_MAX_RETRIES,
    )


def reviewer_agent(state: TripState) -> dict:
    """Reviewer Agent：LLM 审查 + 向所有 Agent 广播审查结论。"""
    raw = state.get("planner_raw")
    trace = {
        "agent": "reviewer",
        "timestamp": datetime.datetime.now().isoformat(),
    }

    if not raw:
        trace["action"] = "quality_check"
        trace["output"] = {"error": "行程数据为空"}
        return {
            "review_passed": False,
            "review_feedback": ["行程数据为空"],
            "enriched_itinerary": None,
            "messages": [{"agent": "reviewer", "type": "verdict",
                          "content": trace, "summary": "Reviewer: 行程数据为空"}],
            "agent_traces": [trace],
        }

    # 检查是否二次审查（Planner 已修正过一次）
    messages = state.get("messages", [])
    is_second_review = any(
        m.get("agent") == "planner" and m.get("type") == "revision"
        for m in messages
    )

    trace["action"] = "quality_check"
    trace["input"] = {
        "days": len(raw.get("days", [])),
        "destination": raw.get("destination"),
        "is_second_review": is_second_review,
    }

    llm = _build_llm()
    verdict = _default_verdict()

    if llm:
        try:
            input_json = json.dumps(raw, ensure_ascii=False, indent=2)[:6000]
            second_review_hint = "\n注意：这是修正后的版本，请检查修正是否到位。" if is_second_review else ""

            response = llm.invoke([
                ("system", REVIEWER_SYSTEM_PROMPT),
                ("human",
                    f"用户偏好: {state.get('preferences', [])}\n"
                    f"节奏: {state.get('pace', '未指定')}\n"
                    f"预算: {state.get('budget', 0)}\n"
                    f"{second_review_hint}\n"
                    f"生成的行程:\n{input_json}"),
            ])
            raw_out = response.content.strip()
            if raw_out.startswith("```"):
                raw_out = raw_out.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            verdict = json.loads(raw_out)

            logger.info(
                "[Reviewer] score=%d/10, passed=%s, issues=%d",
                verdict.get("score", 0), verdict.get("passed", False),
                len(verdict.get("issues", [])),
            )
        except Exception as exc:
            logger.warning("[Reviewer] LLM failed: %s", exc)

    # 规则级过滤
    raw_tips = raw.get("tips", [])
    clean_tips = [
        t for t in raw_tips
        if not any(kw in t for kw in TECH_KEYWORDS)
    ]
    if not clean_tips:
        dest = state.get("normalized_destination") or raw.get("destination", "目的地")
        clean_tips = [f"建议根据{dest}天气准备雨具或薄外套。", "热门景点建议错峰出发。"]

    # 天气补充
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
        logger.warning("[Reviewer] weather: %s", exc)

    enriched = dict(raw)
    enriched["tips"] = clean_tips
    enriched["source_notes"] = ["路线基于本地攻略 + 高德地图生成。"]

    passed = verdict.get("passed", True)
    issues = verdict.get("issues", [])
    suggestions = verdict.get("suggestions", [])
    feedback = issues + suggestions

    trace["output"] = {
        "passed": passed,
        "score": verdict.get("score", 7),
        "issues": issues[:3],
        "suggestions": suggestions[:3],
        "is_second_review": is_second_review,
    }

    # 向所有 Agent 广播审查结论（Planner 会读到这个）
    msg = {
        "agent": "reviewer",
        "type": "verdict",
        "content": trace,
        "summary": (
            f"Reviewer: {'✅ 通过' if passed else '❌ 需修正'}"
            f"（评分 {verdict.get('score', 7)}/10）"
            + (f" 问题: {issues[0][:50]}" if issues else "")
        ),
    }

    return {
        "enriched_itinerary": enriched,
        "review_passed": passed,
        "review_feedback": feedback if not passed else [],
        "messages": [msg],
        "agent_traces": [trace],
    }


def _default_verdict() -> dict:
    return {"passed": True, "score": 7, "issues": [], "suggestions": [], "strengths": []}


def reviewer_should_retry(state: TripState) -> str:
    if state.get("review_passed", False):
        return "end"
    retry = state.get("retry_count", 0)
    if retry < state.get("max_retries", 1):
        return "planner"
    return "end"
