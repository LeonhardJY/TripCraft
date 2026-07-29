from __future__ import annotations

import re


_RAG_CONTEXT_TITLE_PATTERN = re.compile(r"^\[来源:\s*.+?\s*\|\s*标题:\s*(?P<title>.+?)\]$")
_MARKDOWN_HEADING_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)*\s+")
_MEAL_NAME_PATTERN = re.compile(r"【(?P<name>[^】]+)】招牌")
_HOTEL_NAME_PATTERN = re.compile(r"【(?P<name>[^】]+)】[^\n]*预算：\*\*")


def _append_unique(candidates: list[str], value: str | None) -> None:
    normalized = (value or "").strip()
    if normalized and normalized not in candidates:
        candidates.append(normalized)


def _extract_spot_names(rag_contexts: list[str]) -> list[str]:
    candidates: list[str] = []
    for context in rag_contexts:
        header, separator, body = context.partition("\n")
        if not separator or "**位置**" not in body:
            continue

        match = _RAG_CONTEXT_TITLE_PATTERN.match(header.strip())
        if match is None:
            continue
        _append_unique(
            candidates,
            _MARKDOWN_HEADING_NUMBER_PATTERN.sub("", match.group("title")).strip(),
        )
    return candidates


# 从"全部景点一览"表格中提取景点名
_SPOT_TABLE_PATTERN = re.compile(r"^\|\s*(.+?)\s*\|", re.MULTILINE)


def _extract_spot_names_from_tables(rag_contexts: list[str]) -> list[str]:
    candidates: list[str] = []
    for context in rag_contexts:
        for line in context.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            if "名称" in line and "区域" in line:
                continue
            if line.replace("|", "").replace("-", "").strip() == "":
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and parts[0] not in candidates:
                if not any(kw in line for kw in ["人均", "价位", "元/晚"]):
                    candidates.append(parts[0])
    return candidates


def _extract_entity_names(rag_contexts: list[str], pattern: re.Pattern[str]) -> list[str]:
    candidates: list[str] = []
    for context in rag_contexts:
        for match in pattern.finditer(context):
            _append_unique(candidates, match.group("name"))
    return candidates


def extract_fallback_candidates(rag_contexts: list[str]) -> dict[str, list[str]]:
    """按行程 fallback 的正式规则提取真实景点、餐饮和住宿候选。"""
    spots = _extract_spot_names(rag_contexts)
    spots.extend(
        s for s in _extract_spot_names_from_tables(rag_contexts) if s not in spots
    )
    return {
        "spots": spots,
        "meals": _extract_entity_names(rag_contexts, _MEAL_NAME_PATTERN),
        "hotels": _extract_entity_names(rag_contexts, _HOTEL_NAME_PATTERN),
    }
