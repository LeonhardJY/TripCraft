"""Multi-Agent 共享状态定义 — 含 Agent 间通信日志。"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from typing_extensions import TypedDict


def merge_messages(left: list, right: list) -> list:
    """LangGraph 的 reducer：合并新旧消息列表。"""
    return left + right


class TripState(TypedDict):
    """贯穿所有 Agent 的共享状态。

    messages 字段记录 Agent 之间的对话历史，
    每个 Agent 都能读到所有消息，实现真正的双向通信。
    """

    # ---- 输入（不变） ----
    destination: str
    start_date: str
    end_date: str
    travelers: int
    budget: float
    preferences: list[str]
    pace: str | None
    hotel_level: str | None
    dietary_preferences: list[str]
    special_notes: str | None

    # ---- Router Agent 输出 ----
    coverage: str
    normalized_destination: str
    adcode: str | None
    resolution_message: str | None

    # ---- Planner Agent 输出 ----
    rag_context: list[str]
    planner_raw: dict | None
    planner_errors: list[str]

    # ---- Reviewer Agent 输出 ----
    enriched_itinerary: dict | None
    review_passed: bool
    review_feedback: list[str]

    # ---- Agent 间通信日志（新增） ----
    messages: Annotated[list[dict], merge_messages]

    # ---- 暴露给前端的完整调用链路 ----
    agent_traces: list[dict]

    # ---- 循环控制 ----
    retry_count: int
    max_retries: int
