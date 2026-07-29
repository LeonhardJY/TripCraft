from __future__ import annotations

import re
from hashlib import md5
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import (
    BACKEND_DIR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    QDRANT_COLLECTION_NAME,
    QDRANT_URL,
)
from app.rag.guide_catalog import destination_for_guide


DATA_DIR = BACKEND_DIR / "data"


# ---------------------------------------------------------------------------
# Markdown 文本切分
# ---------------------------------------------------------------------------

def _split_markdown_into_chunks(markdown_text: str, source_name: str) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    current_title = "文档开头"
    current_lines: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            if current_lines:
                chunks.append({
                    "title": current_title,
                    "text": "\n".join(current_lines).strip(),
                    "source": source_name,
                })
                current_lines = []
            current_title = stripped.lstrip("#").strip()
        elif stripped:
            current_lines.append(stripped)
    if current_lines:
        chunks.append({
            "title": current_title,
            "text": "\n".join(current_lines).strip(),
            "source": source_name,
        })
    return chunks


def _build_chunk_id(source: str, title: str, text: str) -> str:
    digest = md5(f"{source}|{title}|{text}".encode("utf-8")).hexdigest()
    return f"{source}_{digest}"


def _build_document_text(chunk: dict[str, str]) -> str:
    return f"{chunk['title']}\n{chunk['text']}"


# ---------------------------------------------------------------------------
# 加载攻略片段
# ---------------------------------------------------------------------------

def load_guide_chunks() -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for guide_file in sorted(DATA_DIR.glob("*.md*")):
        destination = destination_for_guide(guide_file.name)
        if destination is None:
            raise ValueError(
                f"攻略文件缺少 destination 映射：{guide_file.name}。"
                "请先在 app/rag/guide_catalog.py 中登记该文件。"
            )
        text = guide_file.read_text(encoding="utf-8")
        raw_chunks = _split_markdown_into_chunks(text, guide_file.name)
        for chunk in raw_chunks:
            chunks.append({
                "id": _build_chunk_id(chunk["source"], chunk["title"], chunk["text"]),
                "title": chunk["title"],
                "text": chunk["text"],
                "source": chunk["source"],
                "destination": destination,
            })
    return chunks


# ---------------------------------------------------------------------------
# 关键词回退检索
# ---------------------------------------------------------------------------

def _extract_keywords(query: str) -> list[str]:
    raw_keywords = re.split(r"[\s,，。；;、]+", query)
    return [kw.strip() for kw in raw_keywords if kw.strip()]


def _score_chunk(query: str, chunk_text: str) -> int:
    keywords = _extract_keywords(query)
    return sum(1 for kw in keywords if kw in chunk_text)


def _search_by_keywords(
    query: str, top_k: int = 3, destination: str | None = None
) -> list[dict[str, str]]:
    scored: list[tuple[int, dict[str, str]]] = []
    for chunk in load_guide_chunks():
        if destination and chunk.get("destination") != destination:
            continue
        score = _score_chunk(query, _build_document_text(chunk))
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


# ---------------------------------------------------------------------------
# Embedding 工具 — Ollama 原生 API / OpenAI-compatible
# ---------------------------------------------------------------------------

def _is_ollama() -> bool:
    url = (LLM_BASE_URL or "").lower()
    return "localhost" in url or "127.0.0.1" in url


def _embed_query_with_usage(
    query: str,
) -> tuple[list[float] | None, dict[str, int]]:
    """调 embedding 接口，返回 (vector, token_usage)。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    # ---- Ollama 原生 API (/api/embed) ----
    if _is_ollama():
        try:
            resp = httpx.post(
                "http://localhost:11434/api/embed",
                json={"model": EMBEDDING_MODEL, "input": query},
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    print(f"[embedding] ollama ok dim={len(embeddings[0])}")
                    return embeddings[0], empty_usage
                print(f"[embedding] ollama empty: {resp.text[:200]}")
            else:
                print(f"[embedding] ollama HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            print(f"[embedding] ollama failed: {type(exc).__name__}: {exc}")
        return None, empty_usage

    # ---- OpenAI-compatible (/v1/embeddings) ----
    base_url = (LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    endpoint = f"{base_url}/embeddings"
    payload = {"model": EMBEDDING_MODEL, "input": query}
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY or 'ollama'}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data") or []
            if items and "embedding" in items[0]:
                usage_data = data.get("usage") or {}
                pt = (
                    usage_data.get("prompt_tokens")
                    or usage_data.get("total_tokens")
                    or 0
                )
                usage = {"prompt_tokens": int(pt), "completion_tokens": 0}
                return items[0]["embedding"], usage
    except Exception as exc:
        print(f"[embedding] API failed: {type(exc).__name__}: {exc}")
    return None, empty_usage


# ---------------------------------------------------------------------------
# 批量 embedding（Ollama / LangChain fallback）
# ---------------------------------------------------------------------------

def _embed_documents(documents: list[str]) -> list[list[float]]:
    """批量 embedding — 优先 Ollama 原生 API，回退 LangChain。"""
    if _is_ollama():
        try:
            resp = httpx.post(
                "http://localhost:11434/api/embed",
                json={"model": EMBEDDING_MODEL, "input": documents},
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                embs = data.get("embeddings", [])
                if embs:
                    print(f"[embedding] ollama batch ok count={len(embs)} dim={len(embs[0])}")
                    return embs
        except Exception as exc:
            print(f"[embedding] ollama batch failed: {type(exc).__name__}: {exc}")

    # OpenAI-compatible fallback
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError:
        # 每段单独调 /api/embed
        results = []
        for doc in documents:
            vec, _ = _embed_query_with_usage(doc)
            if vec:
                results.append(vec)
        return results

    try:
        emb = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=LLM_API_KEY or "ollama",
            base_url=LLM_BASE_URL or None,
            chunk_size=EMBEDDING_BATCH_SIZE,
            check_embedding_ctx_length=False,
        )
    except TypeError:
        emb = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=LLM_API_KEY or "ollama",
            openai_api_base=LLM_BASE_URL or None,
            chunk_size=EMBEDDING_BATCH_SIZE,
            check_embedding_ctx_length=False,
        )
    return emb.embed_documents(documents)  # pyright: ignore


# ---------------------------------------------------------------------------
# Qdrant 客户端与集合管理
# ---------------------------------------------------------------------------

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, timeout=30)
    return _client


_VECTOR_SIZE: int | None = None


def _detect_vector_size() -> int:
    query_vec, _ = _embed_query_with_usage("hello")
    if query_vec:
        return len(query_vec)
    return 768


def _ensure_collection():
    global _VECTOR_SIZE
    client = _get_client()
    collections = client.get_collections().collections
    exists = any(c.name == QDRANT_COLLECTION_NAME for c in collections)
    if _VECTOR_SIZE is None:
        _VECTOR_SIZE = _detect_vector_size()
    if not exists:
        client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"[qdrant] created collection '{QDRANT_COLLECTION_NAME}' (dim={_VECTOR_SIZE})")


# ---------------------------------------------------------------------------
# 数据入库
# ---------------------------------------------------------------------------

def ingest_guide_chunks_to_chroma() -> int:
    """写入 Qdrant（函数名保持兼容）。"""
    _ensure_collection()
    client = _get_client()
    chunks = load_guide_chunks()
    documents = [_build_document_text(c) for c in chunks]
    vectors = _embed_documents(documents)
    if not vectors:
        raise RuntimeError("embedding 全部失败，无法写入 Qdrant。")
    points: list[PointStruct] = []
    for i, chunk in enumerate(chunks):
        points.append(
            PointStruct(
                id=abs(hash(chunk["id"])),
                vector=vectors[i],
                payload={
                    "title": chunk["title"],
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "destination": chunk["destination"],
                    "doc_id": chunk["id"],
                },
            )
        )
    client.recreate_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
    )
    client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)
    print(f"[qdrant] ingested {len(points)} chunks")
    return len(chunks)


# ---------------------------------------------------------------------------
# 向量检索
# ---------------------------------------------------------------------------

def _search_by_qdrant(
    query: str, top_k: int = 3, destination: str | None = None
) -> tuple[list[dict[str, str]], dict[str, int]]:
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    try:
        client = _get_client()
        cols = client.get_collections().collections
        if not any(c.name == QDRANT_COLLECTION_NAME for c in cols):
            return [], empty_usage
    except Exception:
        return [], empty_usage

    query_vec, embedding_usage = _embed_query_with_usage(query)
    if query_vec is None:
        return [], empty_usage

    qfilter = None
    if destination:
        qfilter = Filter(must=[FieldCondition(key="destination", match=MatchValue(value=destination))])

    try:
        results = client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_vec,
            limit=top_k,
            query_filter=qfilter,
        )
    except Exception as exc:
        print(f"[qdrant] search failed: {exc}")
        return [], empty_usage

    matched: list[dict[str, str]] = []
    for res in results:
        p = res.payload or {}
        matched.append({
            "title": p.get("title", ""),
            "text": p.get("text", ""),
            "source": p.get("source", ""),
            "destination": p.get("destination", ""),
        })
    return matched, embedding_usage


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def search_guide_chunks_with_usage(
    query: str, top_k: int = 3, destination: str | None = None
) -> tuple[list[dict[str, str]], dict[str, int]]:
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    vec_results, emb_usage = _search_by_qdrant(query=query, top_k=top_k, destination=destination)
    if vec_results:
        return vec_results, emb_usage
    return _search_by_keywords(query=query, top_k=top_k, destination=destination), empty_usage


def search_guide_chunks(
    query: str, top_k: int = 3, destination: str | None = None
) -> list[dict[str, str]]:
    chunks, _ = search_guide_chunks_with_usage(query=query, top_k=top_k, destination=destination)
    return chunks
