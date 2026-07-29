"""RAG 检索、规则级重排序与缓存。

与 Qdrant 向量库配合，去掉了 DashScope Rerank 外部依赖，
所有重排序走规则级；保留相同的对外函数接口。
"""

import hashlib
import logging
import re

from app.config import REDIS_RAG_TTL_SECONDS
from app.rag.vector_db import search_guide_chunks_with_usage
from app.services.cache_service import get_cached_json, set_cached_json


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _normalize_cache_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _extract_keywords(query: str) -> list[str]:
    raw = re.split(r"[\s,，。；;、]+", query)
    return [p.strip() for p in raw if p.strip()]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


_NOISE_TITLES = {"文档开头"}


# ---------------------------------------------------------------------------
# 规则级重排序（原 DashScope Rerank 的 fallback，现作为唯一方法）
# ---------------------------------------------------------------------------

def _score_chunk_for_rerank(
    query: str,
    chunk: dict[str, str],
    destination: str | None = None,
) -> int:
    """基于关键词和领域规则给片段打分。"""
    title = chunk.get("title", "")
    text = chunk.get("text", "")
    source = chunk.get("source", "")
    reasons: list[str] = []
    score = 0

    for kw in _extract_keywords(query):
        if kw in title:
            score += 3
            reasons.append(f"title+3:{kw}")
        if kw in text:
            score += 1
            reasons.append(f"text+1:{kw}")

    # 噪声降权
    if title in _NOISE_TITLES:
        score -= 8
        reasons.append("noise-8:文档开头")

    if "行程" in title and "行程参考" not in title:
        score += 4
        reasons.append("domain+4:行程标题")

    if "行程参考" in title:
        score -= 4
        reasons.append("domain-4:行程参考降权")

    if "目的地简介" in title:
        score -= 2
        reasons.append("domain-2:目的地简介降权")

    if _contains_any(title, ["餐饮", "预算"]) and not _contains_any(
        text, ["日落", "傍晚", "拍照", "摄影", "出片", "洱海", "双廊", "慢节奏"]
    ):
        score -= 3
        reasons.append("domain-3:餐饮预算弱相关")

    if destination:
        cd = chunk.get("destination", "")
        if cd and cd != destination:
            score -= 5
            reasons.append(f"dest-5:metadata={cd}")
        elif not cd:
            chunk_lower = f"{source} {title} {text}".lower()
            if destination.lower() not in chunk_lower:
                score -= 5
                reasons.append(f"dest-5:缺失元数据且非{destination}片段")

    chunk["rerank_reasons"] = reasons
    return score


# ---------------------------------------------------------------------------
# 重排序入口（去掉 DashScope API，仅规则级）
# ---------------------------------------------------------------------------

def rerank_guide_chunks(
    query: str,
    matched_chunks: list[dict[str, str]],
    top_k: int,
    destination: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """
    对召回候选做规则级重排序。
    返回 (chunks, rerank_token_usage) — 本地规则级 token_usage 为空。
    """
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    cache_key = _build_rerank_cache_key(query, matched_chunks)

    cached = get_cached_json(cache_key)
    if cached is not None:
        reranked: list[dict[str, str]] = []
        for item in cached:
            idx = item["i"]
            if 0 <= idx < len(matched_chunks):
                enriched = dict(matched_chunks[idx])
                enriched["rerank_score"] = item["s"]
                enriched["rerank_reasons"] = [f"rule-based:{item['s']}"]
                reranked.append(enriched)
        return reranked[:top_k], empty_usage

    scored: list[tuple[int, int, dict[str, str]]] = []
    for idx, chunk in enumerate(matched_chunks):
        enriched = dict(chunk)
        s = _score_chunk_for_rerank(query, enriched, destination=destination)
        enriched["rerank_score"] = s
        scored.append((s, -idx, enriched))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    result = [c for _, _, c in scored[:top_k]]

    # 写入缓存
    cache_value = [{"i": chunk["rerank_score"], "s": 0} for chunk in result]
    set_cached_json(cache_key, cache_value, expire_seconds=REDIS_RAG_TTL_SECONDS)

    return result, empty_usage


def _build_rerank_cache_key(query: str, chunks: list[dict[str, str]]) -> str:
    normalized_query = _normalize_cache_text(query)
    fingerprint = "|".join(
        f"{c.get('source', '')}:{c.get('title', '')}" for c in chunks
    )
    h = hashlib.md5(fingerprint.encode()).hexdigest()[:12]
    return f"rerank:{normalized_query}:{h}"


# ---------------------------------------------------------------------------
# 对外接口（保持原有签名）
# ---------------------------------------------------------------------------

def retrieve_travel_guide_chunks(
    query: str, top_k: int = 3, destination: str | None = None
) -> tuple[list[dict[str, str]], dict[str, int], dict[str, int]]:
    """返回带规则级 rerank 的原始攻略片段。返回 (chunks, rerank_usage, embedding_usage)。"""
    candidate_k = max(top_k * 2, 6)
    kwargs: dict = {"query": query, "top_k": candidate_k}
    if destination:
        kwargs["destination"] = destination
    matched_chunks, embedding_usage = search_guide_chunks_with_usage(**kwargs)
    reranked_chunks, rerank_usage = rerank_guide_chunks(
        query=query, matched_chunks=matched_chunks,
        top_k=top_k, destination=destination,
    )
    return reranked_chunks, rerank_usage, embedding_usage


def retrieve_travel_guide(
    query: str, top_k: int = 3, destination: str | None = None
) -> tuple[list[str], dict[str, int], dict[str, int]]:
    """返回最相关的攻略片段。返回 (texts, rerank_usage, embedding_usage)。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    cache_destination = destination or "all"
    cache_key = f"rag:guide:{cache_destination}:{_normalize_cache_text(query)}:{top_k}"
    cached = get_cached_json(cache_key)
    if cached is not None:
        logger.info("rag cache hit: query=%s top_k=%s", query, top_k)
        return [str(item) for item in cached], empty_usage, empty_usage

    matched_chunks, rerank_usage, embedding_usage = retrieve_travel_guide_chunks(
        query=query, top_k=top_k, destination=destination
    )

    results = [
        f"[来源: {chunk['source']} | 标题: {chunk['title']}]\n{chunk['text']}"
        for chunk in matched_chunks
    ]

    set_cached_json(cache_key, results, expire_seconds=REDIS_RAG_TTL_SECONDS)
    return results, rerank_usage, embedding_usage
