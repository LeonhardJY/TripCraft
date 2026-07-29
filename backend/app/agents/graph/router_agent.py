"""Router Agent — 真 LLM 决策。

每个 Router Agent 独立调用 LLM，根据目的地判断覆盖等级。
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
from app.rag.guide_catalog import known_destinations

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """你是一个旅行规划路由专家。你的职责是分析用户输入的目的地，判断最适合的规划路径。

已知以下城市已有深度本地攻略（curated 路径）：
{curated_cities}

对于这些城市，系统可以基于本地攻略知识库生成高质量行程。

对于攻略未覆盖但具体有效的城市（如昆明、杭州、南京），走 dynamic 路径，
系统会从地图服务获取 POI 候选数据。

对于省份名称（如"云南""浙江""青海"）或无法识别的区域，返回 unsupported。

判断时要考虑：
- 用户输入的是具体城市还是省份
- 该城市是否在 curated 列表中
- 城市别名或俗称（如"春城"=昆明、"蓉城"=成都）

返回 JSON 格式（不要 markdown 包裹）：
{{"tier": "curated"|"dynamic"|"unsupported",
  "canonical_city": "规范化城市名称",
  "reason": "判断理由"}}
"""


class RouterDecision(BaseModel):
    """Router Agent 的结构化输出。"""
    tier: str = Field(..., pattern="^(curated|dynamic|unsupported)$")
    canonical_city: str = Field(..., description="规范化后的城市名称")
    reason: str = Field(..., description="判断理由")


def _build_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.1,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def router_agent(state: TripState) -> dict:
    """Router Agent：LLM 独立判断目的地覆盖等级。"""
    destination = state.get("destination", "")
    if not destination:
        return {
            "coverage": "unsupported",
            "normalized_destination": "",
            "resolution_message": "目的地不能为空。",
        }

    curated = "、".join(sorted(known_destinations()))
    prompt = ROUTER_SYSTEM_PROMPT.format(curated_cities=curated)

    llm = _build_llm()
    if not llm:
        # fallback: 无 LLM 时走简单规则
        return _rule_fallback(destination)

    try:
        response = llm.invoke([
            ("system", prompt),
            ("human", f"用户输入的目的地: {destination}"),
        ])
        raw = response.content.strip()
        # 清理可能的 markdown 包裹
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        decision = json.loads(raw)
        tier = decision.get("tier", "unsupported")
        canonical = decision.get("canonical_city", destination)

        logger.info(
            "[RouterAgent·LLM] %s → tier=%s canonical=%s reason=%s",
            destination, tier, canonical, decision.get("reason", ""),
        )

        if tier not in ("curated", "dynamic"):
            return {
                "coverage": "unsupported",
                "normalized_destination": canonical,
                "resolution_message": decision.get("reason", f"无法规划「{destination}」"),
            }

        return {
            "coverage": tier,
            "normalized_destination": canonical,
            "resolution_message": None,
        }

    except Exception as exc:
        logger.warning("[RouterAgent] LLM failed, fallback to rule: %s", exc)
        return _rule_fallback(destination)


def _rule_fallback(destination: str) -> dict:
    """LLM 不可用时的规则级 fallback。"""
    from app.services.city_resolver_service import resolve_city
    try:
        result = resolve_city(destination)
        tier = result.tier.value if hasattr(result.tier, "value") else str(result.tier)
        if tier == "curated":
            return {
                "coverage": "curated",
                "normalized_destination": result.city,
                "resolution_message": None,
            }
        elif tier == "dynamic":
            return {
                "coverage": "dynamic",
                "normalized_destination": result.city,
                "adcode": result.adcode,
                "resolution_message": None,
            }
        else:
            return {
                "coverage": "unsupported",
                "normalized_destination": destination,
                "resolution_message": f"无法规划「{destination}」",
            }
    except Exception:
        return {
            "coverage": "unsupported",
            "normalized_destination": destination,
            "resolution_message": f"无法解析目的地「{destination}」",
        }


def router_should_continue(state: TripState) -> str:
    coverage = state.get("coverage", "unsupported")
    return "end" if coverage == "unsupported" else "planner"
