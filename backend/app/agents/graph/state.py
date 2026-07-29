"""Multi-Agent 共享状态定义。"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from langgraph.graph import add_messages
from typing_extensions import TypedDict


class TripState(TypedDict):
    """贯穿所有 Agent 的共享状态。

    LangGraph 的 State 是每次 node 返回后自动 merge 的字典。
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
    coverage: str                      # "curated" | "dynamic" | "unsupported"
    normalized_destination: str        # 规范化后的目的地名称
    adcode: str | None                 # 高德行政区代码（dynamic 用）
    resolution_message: str | None     # 错误或提示信息

    # ---- Planner Agent 输入/输出 ----
    rag_context: list[str]             # RAG 检索结果文本
    planner_raw: dict | None           # LLM 原始输出
    planner_errors: list[str]          # 规划阶段错误

    # ---- Reviewer Agent ----
    enriched_itinerary: dict | None    # 最终行程
    review_passed: bool
    review_feedback: list[str]         # Reviewer 的改进建议

    # ---- 循环控制 ----
    retry_count: int
    max_retries: int
