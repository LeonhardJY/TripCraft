"""Multi-Agent StateGraph — Agent 间通过 messages 双向通信。"""

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

    workflow.add_conditional_edges(
        "router",
        router_should_continue,
        {"planner": "planner", "end": END},
    )
    workflow.add_conditional_edges(
        "planner",
        planner_should_retry,
        {"reviewer": "reviewer", "end": END},
    )
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
    """入口：用户请求 → Multi-Agent 协作 → 最终行程 + 通信日志。"""
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
        "messages": [],
        "agent_traces": [],
        "retry_count": 0,
        "max_retries": 1,
    }

    # 第一轮
    result = graph.invoke(initial)

    # 检查是否需要重试（Reviewer 未通过且有反馈）
    retry = 0
    max_r = result.get("max_retries", 1)
    while (
        not result.get("review_passed", False)
        and result.get("review_feedback")
        and retry < max_r
    ):
        retry += 1
        result["retry_count"] = retry
        # 清空旧的 reviewer 状态，Planner 会从 messages 读反馈
        result["planner_errors"] = []
        result["review_feedback"] = []
        result["enriched_itinerary"] = None
        logger.info("[Graph] retry %d/%d — Planner 收到 Reviewer 反馈", retry, max_r)
        result = graph.invoke(result)

    # 收集所有 agent_traces
    all_traces: list[dict] = []
    for msg in result.get("messages", []):
        content = msg.get("content", {})
        if content:
            all_traces.append(content)
    result["agent_traces"] = all_traces

    return result


def format_conversation_log(state: dict) -> str:
    """把 Agent 对话历史格式化为可读文本，用于展示。"""
    lines = ["=== Multi-Agent 协作日志 ==="]
    for msg in state.get("messages", []):
        summary = msg.get("summary", "")
        if summary:
            lines.append(f"  {summary}")
    return "\n".join(lines)


__all__ = ["run_trip_graph", "get_graph", "format_conversation_log"]
