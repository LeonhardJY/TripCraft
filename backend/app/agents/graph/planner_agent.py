"""Planner Agent — 行程生成。

封装 trip_service 中已有的生成逻辑为 LangGraph Node。
"""

from __future__ import annotations

import logging
from datetime import date

from app.agents.graph.state import TripState
from app.models.schemas import TripRequest
from app.services.trip_service import (
    generate_dynamic_trip_itinerary,
    generate_trip_itinerary,
)
from app.services.place_candidate_service import collect_city_candidate_pool

logger = logging.getLogger(__name__)


def planner_agent(state: TripState) -> dict:
    """根据 Router 的覆盖等级调用对应的行程生成逻辑。"""
    coverage = state.get("coverage", "curated")
    errors: list[str] = []

    request = _build_request(state)

    try:
        if coverage == "curated":
            itinerary = generate_trip_itinerary(request)
        elif coverage == "dynamic":
            adcode = state.get("adcode")
            if not adcode:
                return {"planner_errors": ["动态城市缺少行政区代码"]}
            pool = collect_city_candidate_pool(
                request.destination, adcode
            )
            if not pool or not pool.is_valid():
                return {"planner_errors": [f"「{request.destination}」候选数据不足"]}
            itinerary = generate_dynamic_trip_itinerary(request, pool)
        else:
            return {"planner_errors": [f"不支持的覆盖等级: {coverage}"]}

        return {
            "planner_raw": itinerary.model_dump(),
            "planner_errors": [],
        }

    except Exception as exc:
        logger.error("[PlannerAgent] failed: %s", exc)
        return {"planner_errors": [f"行程生成失败: {exc}"]}


def _build_request(state: TripState) -> TripRequest:
    """从 TripState 构建 TripRequest。"""
    return TripRequest(
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


def planner_should_retry(state: TripState) -> str:
    errors = state.get("planner_errors", [])
    if errors:
        return "end"
    return "reviewer"
