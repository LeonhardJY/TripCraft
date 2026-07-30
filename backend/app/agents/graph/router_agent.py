"""Router Agent — LLM 决策 + 向所有 Agent 广播目的地分析结果。"""

from __future__ import annotations

import json
import logging
import datetime

from langchain_openai import ChatOpenAI

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

ROUTER_SYSTEM_PROMPT = """你是一个旅行规划路由专家。分析用户输入的目的地，判断最适合的规划路径。

已知深度攻略城市：{curated_cities}
这些城市可以基于本地攻略生成高质量行程。

对于攻略未覆盖但有效的城市（如昆明、杭州），走 dynamic 路径。
对于省份名称或无法识别的区域（如"云南""火星"），返回 unsupported。

注意理解常见别名：春城=昆明、蓉城=成都、羊城=广州、魔都=上海。

返回 JSON（不要 markdown 包裹）：
{{"tier": "curated"|"dynamic"|"unsupported",
  "canonical_city": "规范化城市名称",
  "reason": "判断理由"}}
"""


def _build_llm():
    return ChatOpenAI(
        model=LLM_MODEL, temperature=0.1,
        api_key=LLM_API_KEY, base_url=LLM_BASE_URL or None,
        timeout=LLM_TIMEOUT_SECONDS, max_retries=LLM_MAX_RETRIES,
    )


def router_agent(state: TripState) -> dict:
    """Router Agent：LLM 决策后，向所有 Agent 广播分析结果。"""
    destination = state.get("destination", "")
    trace = {
        "agent": "router",
        "action": "destination_analysis",
        "input": {"destination": destination},
        "timestamp": datetime.datetime.now().isoformat(),
    }

    if not destination:
        trace["output"] = {"tier": "unsupported", "reason": "目的地为空"}
        return {
            "coverage": "unsupported",
            "normalized_destination": "",
            "resolution_message": "目的地不能为空。",
            "messages": [{"agent": "router", "type": "decision", "content": trace}],
            "agent_traces": [trace],
        }

    curated = "、".join(sorted(known_destinations()))
    llm = _build_llm()

    try:
        response = llm.invoke([
            ("system", ROUTER_SYSTEM_PROMPT.format(curated_cities=curated)),
            ("human", f"目的地: {destination}"),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        decision = json.loads(raw)
        tier = decision.get("tier", "unsupported")
        canonical = decision.get("canonical_city", destination)
        reason = decision.get("reason", "")

        logger.info("[Router] %s → %s (%s)", destination, tier, canonical)

        trace["output"] = {"tier": tier, "canonical_city": canonical, "reason": reason}
        message = {
            "agent": "router",
            "type": "decision",
            "content": trace,
            "summary": f"Router: 将「{destination}」判定为 {tier}（规范化: {canonical}）",
        }

        if tier not in ("curated", "dynamic"):
            return {
                "coverage": "unsupported",
                "normalized_destination": canonical,
                "resolution_message": reason or f"无法规划「{destination}」",
                "messages": [message],
                "agent_traces": [trace],
            }

        return {
            "coverage": tier,
            "normalized_destination": canonical,
            "resolution_message": None,
            "messages": [message],
            "agent_traces": [trace],
        }

    except Exception as exc:
        logger.warning("[Router] LLM failed: %s", exc)
        return _rule_fallback(destination, trace)


def _rule_fallback(destination: str, trace: dict) -> dict:
    from app.services.city_resolver_service import resolve_city
    try:
        result = resolve_city(destination)
        tier = "curated" if result.tier.value == "curated" else "dynamic"
        trace["output"] = {"tier": tier, "canonical_city": result.city, "reason": "规则 fallback"}
        return {
            "coverage": tier,
            "normalized_destination": result.city,
            "adcode": result.adcode,
            "messages": [{"agent": "router", "type": "decision", "content": trace,
                          "summary": f"Router(fallback): {destination} → {tier}"}],
            "agent_traces": [trace],
        }
    except Exception:
        trace["output"] = {"tier": "unsupported", "reason": "解析失败"}
        return {
            "coverage": "unsupported", "normalized_destination": destination,
            "resolution_message": f"无法解析「{destination}」",
            "messages": [{"agent": "router", "type": "decision", "content": trace}],
            "agent_traces": [trace],
        }


def router_should_continue(state: TripState) -> str:
    return "end" if state.get("coverage") == "unsupported" else "planner"
