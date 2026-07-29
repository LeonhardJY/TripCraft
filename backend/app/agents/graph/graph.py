"""Multi-Agent StateGraph。

Agent 分工：
  Router  → 目的地解析与路径分派
  Planner → RAG 检索 + LLM 行程生成
  Reviewer → 质量检查 + 天气补充 + 过滤技术提示

流程：
  START → Router ──→ Planner ──→ Reviewer ──→ END
                       ↑            │ (重试)
                       └──────────────┘
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.graph.state import TripState
from app.agents.graph.router_agent import router_agent, router_should_continue
from app.agents.graph.planner_agent import planner_agent, planner_should_retry
from app.agents.graph.reviewer_agent import reviewer_agent, reviewer_should_retry

logger = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    workflow = StateGraph(TripState)

    workflow.add_node("router", router_agent)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("reviewer", reviewer_agent)

    workflow.set_entry_point("router")

    # Router → Planner 或 END
    workflow.add_conditional_edges(
        "router",
        router_should_continue,
        {"planner": "planner", "end": END},
    )

    # Planner → Reviewer 或 END（出错）
    workflow.add_conditional_edges(
        "planner",
        planner_should_retry,
        {"reviewer": "reviewer", "end": END},
    )

    # Reviewer → END（通过）/ Planner（重试）/ END（超限）
    workflow.add_conditional_edges(
        "reviewer",
        reviewer_should_retry,
        {"planner": "planner", "end": END},
    )

    return workflow.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def run_trip_graph(user_input: dict) -> dict[str, Any]:
    """外部入口：输入用户请求 → 输出最终行程。"""
    graph = get_graph()

    initial: TripState = {
        "destination": user_input.get("destination", ""),
        "start_date": user_input.get("start_date", ""),
        "end_date": user_input.get("end_date", ""),
        "travelers": user_input.get("travelers", 1),
        "budget": float(user_input.get("budget", 0)),
        "preferences": user_input.get("preferences", []),
        "pace": user_input.get("pace"),
        "hotel_level": user_input.get("hotel_level"),
        "dietary_preferences": user_input.get("dietary_preferences", []),
        "special_notes": user_input.get("special_notes"),
        "coverage": "",
        "normalized_destination": "",
        "adcode": None,
        "resolution_message": None,
        "rag_context": [],
        "planner_raw": None,
        "planner_errors": [],
        "enriched_itinerary": None,
        "review_passed": False,
        "review_feedback": [],
        "retry_count": 0,
        "max_retries": 1,
    }

    result = graph.invoke(initial)

    # 手动处理重试循环
    retry = 0
    while (
        not result.get("review_passed", False)
        and result.get("planner_errors")
        and retry < result.get("max_retries", 1)
    ):
        retry += 1
        result["retry_count"] = retry
        result["planner_errors"] = []
        result["review_feedback"] = []
        result = graph.invoke(result)

    return result


__all__ = ["run_trip_graph", "get_graph"]
