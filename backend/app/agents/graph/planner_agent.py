"""Planner Agent — 行程生成 + 支持根据 Reviewer 反馈修正。"""

from __future__ import annotations

import datetime
import json
import logging
from datetime import date

from langchain_openai import ChatOpenAI

from app.agents.graph.state import TripState
from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TIMEOUT_SECONDS,
)
from app.models.schemas import TripRequest
from app.services.trip_service import (
    generate_dynamic_trip_itinerary,
    generate_trip_itinerary,
)
from app.services.place_candidate_service import collect_city_candidate_pool

logger = logging.getLogger(__name__)

REVISE_SYSTEM_PROMPT = """你是一个行程修正专家。Reviewer 对之前生成的行程提出了改进意见。
请根据 Reviewer 的具体反馈，对原行程做**精准修改**而不是重新生成。

Reviewer 反馈：{feedback}

保留原行程的框架（天数、预算结构、目的地），只修正反馈中指出的问题。
输出 JSON 格式的完整修正后行程。
"""


def planner_agent(state: TripState) -> dict:
    """
    Planner Agent:
      - 首次运行：调用 trip_service 生成行程
      - 重试运行：读取 Reviewer 反馈，对已有行程做针对性修正
    """
    coverage = state.get("coverage", "curated")
    trace = {
        "agent": "planner",
        "timestamp": datetime.datetime.now().isoformat(),
    }

    # 检查是否是重试（有 reviewer 反馈）
    messages = state.get("messages", [])
    reviewer_feedback = _find_reviewer_feedback(messages)

    if reviewer_feedback and state.get("planner_raw"):
        return _revise_itinerary(state, reviewer_feedback, trace)
    else:
        return _generate_itinerary(state, coverage, trace)


def _find_reviewer_feedback(messages: list[dict]) -> str | None:
    """从消息历史中找到最近的 Reviewer 反馈。"""
    for msg in reversed(messages):
        if msg.get("agent") == "reviewer" and msg.get("type") == "verdict":
            feedback = msg.get("content", {}).get("feedback", [])
            if feedback:
                return "\n".join(feedback)
    return None


def _generate_itinerary(state: TripState, coverage: str, trace: dict) -> dict:
    """首次行程生成。"""
    request = TripRequest(
        destination=state.get("normalized_destination") or state.get("destination", ""),
        start_date=date.fromisoformat(state.get("start_date", "2026-01-01")),
        end_date=date.fromisoformat(state.get("end_date", "2026-01-03")),
        travelers=state.get("travelers", 1),
        budget=float(state.get("budget", 0)),
        preferences=state.get("preferences", []),
        pace=state.get("pace"),
        hotel_level=state.get("hotel_level"),
        dietary_preferences=state.get("dietary_preferences", []),
        special_notes=state.get("special_notes"),
    )

    trace["action"] = "generate_draft"
    trace["input"] = {"destination": request.destination, "coverage": coverage}

    try:
        if coverage == "curated":
            itinerary = generate_trip_itinerary(request)
        elif coverage == "dynamic":
            adcode = state.get("adcode")
            pool = collect_city_candidate_pool(request.destination, adcode)
            if not pool or not pool.is_valid():
                raise ValueError("候选数据不足")
            itinerary = generate_dynamic_trip_itinerary(request, pool)
        else:
            return {"planner_errors": [f"不支持: {coverage}"]}

        data = itinerary.model_dump()
        trace["output"] = {
            "summary": data.get("summary", "")[:80],
            "days": len(data.get("days", [])),
            "budget": data.get("estimated_budget"),
        }

        msg_summary = f"Planner: 生成 {request.destination} {len(data.get('days',[]))} 天行程，预算 ¥{data.get('estimated_budget',0):.0f}"
        message = {
            "agent": "planner",
            "type": "draft",
            "content": trace,
            "summary": msg_summary,
        }

        return {
            "planner_raw": data,
            "planner_errors": [],
            "messages": [message],
            "agent_traces": [trace],
        }

    except Exception as exc:
        logger.error("[Planner] failed: %s", exc)
        return {"planner_errors": [f"生成失败: {exc}"]}


def _revise_itinerary(state: TripState, feedback: str, trace: dict) -> dict:
    """根据 Reviewer 反馈修正既有行程。"""
    existing = state.get("planner_raw", {})
    trace["action"] = "revise_draft"
    trace["input"] = {
        "feedback": feedback,
        "existing_days": len(existing.get("days", [])),
    }

    prompt = REVISE_SYSTEM_PROMPT.format(feedback=feedback)
    dest = state.get("normalized_destination") or existing.get("destination", "")

    llm = ChatOpenAI(
        model=LLM_MODEL, temperature=0.3,
        api_key=LLM_API_KEY, base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS, max_retries=LLM_MAX_RETRIES,
    )
    if not llm:
        # fallback: 直接返回原行程
        trace["output"] = {"note": "LLM 不可用，保持原行程"}
        return {
            "planner_raw": existing,
            "planner_errors": [],
            "messages": [{"agent": "planner", "type": "revision",
                          "content": trace,
                          "summary": f"Planner: LLM 不可用，保持原行程"}],
            "agent_traces": [trace],
        }

    try:
        input_json = json.dumps(existing, ensure_ascii=False, indent=2)[:6000]
        response = llm.invoke([
            ("system", prompt),
            ("human", f"目的地: {dest}\n用户偏好: {state.get('preferences', [])}\n\n原行程 JSON:\n{input_json}"),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        revised = json.loads(raw)
        trace["output"] = {
            "summary": revised.get("summary", "")[:80],
            "days": len(revised.get("days", [])),
            "based_on_feedback": feedback[:80],
        }
        message = {
            "agent": "planner",
            "type": "revision",
            "content": trace,
            "summary": f"Planner: 根据 Reviewer 反馈修正行程（{feedback[:50]}…）",
        }

        return {
            "planner_raw": revised,
            "planner_errors": [],
            "messages": [message],
            "agent_traces": [trace],
        }

    except Exception as exc:
        logger.warning("[Planner] revision failed: %s", exc)
        trace["output"] = {"note": f"修正失败: {exc}，保持原行程"}
        return {
            "planner_raw": existing,
            "planner_errors": [],
            "messages": [{"agent": "planner", "type": "revision",
                          "content": trace,
                          "summary": f"Planner: 修正失败，保持原行程"}],
            "agent_traces": [trace],
        }


def planner_should_retry(state: TripState) -> str:
    errors = state.get("planner_errors", [])
    if errors:
        return "end"
    return "reviewer"
