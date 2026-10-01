import hashlib
import importlib
import json
import os
import pkgutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import requests

import corpus_sources

BASE_DIR = Path(__file__).resolve().parent
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
AUDIT_PATH = BASE_DIR / "rag-audit.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"

COLLECTION_NAME = "supply_chain_unified_context"
EMBED_VECTOR_SIZE = 256

_collection = None
_last_corpus_chunks: list[dict[str, Any]] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Deterministic local embedding (no external embedding API required)."""
    vectors: list[list[float]] = []
    for text in texts:
        values = [0.0] * EMBED_VECTOR_SIZE
        tokens = (text or "").lower().split()
        if not tokens:
            vectors.append(values)
            continue
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i, byte in enumerate(digest):
                idx = i % EMBED_VECTOR_SIZE
                values[idx] += (byte / 255.0) - 0.5
        norm = sum(v * v for v in values) ** 0.5
        if norm > 0:
            values = [v / norm for v in values]
        vectors.append(values)
    return vectors


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def reset_collection() -> None:
    global _collection
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)


def append_audit(tool_name, tool_input, tool_output, validation_status, outcome, start_time):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int((time.time() - start_time) * 1000)
    record = {
        "request_id": str(uuid.uuid4()),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "validation_status": validation_status,
        "outcome": outcome,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def discover_corpus_sources():
    """Finds every module in corpus_sources/ and returns those with a
    load_chunks() function - this is what makes adding a new feature's
    corpus a one-file change, with zero edits to this file."""
    modules = []
    for _, module_name, _ in pkgutil.iter_modules(corpus_sources.__path__):
        module = importlib.import_module(f"corpus_sources.{module_name}")
        if hasattr(module, "load_chunks"):
            modules.append((module_name, module))
    return modules


def load_repository_chunks() -> list[dict[str, Any]]:
    """Low-priority structural context: a listing of files in the shared
    ai-services/ directory itself, tier_3 (lowest authority)."""
    ignored = {".git", ".venv", "__pycache__", "node_modules", "chroma"}
    files: list[str] = []
    for root, dirs, filenames in os.walk(BASE_DIR, topdown=True, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if d not in ignored]
        for filename in filenames:
            try:
                files.append(str((Path(root) / filename).relative_to(BASE_DIR)))
            except ValueError:
                continue
    text = "ai-services repository files include: " + ", ".join(sorted(files[:300]))
    return [{
        "chunk_id": "repo_index",
        "source_id": "repository",
        "authority_tier": "tier_3",
        "text": text,
        "metadata": {"source_type": "repository", "file_count": len(files)},
        "indexed_at": now_iso(),
    }]


def build_corpus() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for module_name, module in discover_corpus_sources():
        try:
            module_chunks = module.load_chunks()
            chunks.extend(module_chunks)
        except Exception as exc:
            chunks.append({
                "chunk_id": f"{module_name}_error",
                "source_id": module_name,
                "authority_tier": "tier_1",
                "text": f"Error loading corpus source '{module_name}': {exc}",
                "metadata": {"source_type": "error", "feature": module_name},
                "indexed_at": now_iso(),
            })
    chunks.extend(load_repository_chunks())
    return chunks


def write_corpus(chunks: list[dict[str, Any]]) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")


def read_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    chunks = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return chunks


def lexical_fallback_retrieve(query: str, k: int) -> list[dict[str, Any]]:
    corpus = _last_corpus_chunks or read_corpus()
    query_tokens = set((query or "").lower().split())
    tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}

    scored = []
    for chunk in corpus:
        text = chunk.get("text", "")
        overlap = len(query_tokens.intersection(set(text.lower().split())))
        scored.append({
            "rank": 0,
            "chunk_id": chunk.get("chunk_id"),
            "source_id": chunk.get("source_id"),
            "authority_tier": chunk.get("authority_tier"),
            "distance": None,
            "text": text,
            "_score": overlap,
        })

    scored.sort(key=lambda r: (tier_weight.get(r.get("authority_tier"), 0), r.get("_score", 0)), reverse=True)
    top = scored[:max(k, 1)]
    for i, row in enumerate(top, start=1):
        row["rank"] = i
        row.pop("_score", None)
    return top


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    global _last_corpus_chunks
    start = time.time()
    try:
        chunks = build_corpus()
        _last_corpus_chunks = chunks
        write_corpus(chunks)
        vector_store_status = "ready"
        vector_store_error = None

        try:
            reset_collection()
            collection = get_collection()
            if chunks:
                ids = [c["chunk_id"] for c in chunks]
                docs = [c["text"] for c in chunks]
                metas = [{"source_id": c["source_id"], "authority_tier": c["authority_tier"], "indexed_at": c["indexed_at"]} for c in chunks]
                embeddings = embed_texts(docs)
                collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        except Exception as exc:
            vector_store_status = "degraded"
            vector_store_error = str(exc)

        sources_loaded = [name for name, _ in discover_corpus_sources()]
        output = {
            "status": "success",
            "caller": caller,
            "chunk_count": len(chunks),
            "sources_loaded": sources_loaded,
            "collection": COLLECTION_NAME,
            "corpus_path": str(CORPUS_PATH),
            "vector_store_status": vector_store_status,
        }
        if vector_store_error:
            output["vector_store_error"] = vector_store_error
        append_audit("refresh_corpus", {"caller": caller}, output, "pass", "corpus_refreshed", start)
        return output
    except Exception as exc:
        output = {"status": "error", "error": str(exc)}
        append_audit("refresh_corpus", {"caller": caller}, output, "fail", "error", start)
        return output


def retrieve_context(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    start = time.time()
    try:
        retrieval_mode = "vector"
        ranked = []
        try:
            collection = get_collection()
            if collection.count() == 0:
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    raise RuntimeError("empty_collection")

            query_embedding = embed_texts([query])
            results = collection.query(query_embeddings=query_embedding, n_results=k)
            ids = (results.get("ids") or [[]])[0]
            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]

            for i, chunk_id in enumerate(ids):
                row_meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
                ranked.append({
                    "rank": i + 1,
                    "chunk_id": chunk_id,
                    "source_id": row_meta.get("source_id"),
                    "authority_tier": row_meta.get("authority_tier"),
                    "distance": distances[i] if i < len(distances) else None,
                    "text": docs[i] if i < len(docs) else "",
                })

            tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}
            ranked.sort(
                key=lambda x: (
                    tier_weight.get(x.get("authority_tier"), 0),
                    -(x.get("distance") if isinstance(x.get("distance"), (int, float)) else 1e9),
                ),
                reverse=True,
            )
        except Exception:
            retrieval_mode = "lexical_fallback"
            if not _last_corpus_chunks and not CORPUS_PATH.exists():
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    return {"status": "error", "error": "corpus_unavailable"}
            ranked = lexical_fallback_retrieve(query, k)

        output = {
            "status": "success",
            "query": query,
            "caller": caller,
            "k": k,
            "retrieval_mode": retrieval_mode,
            "results": ranked,
        }
        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller},
            {"result_count": len(ranked), "chunk_ids": [r["chunk_id"] for r in ranked]},
            "pass", "context_retrieved", start,
        )
        return output
    except Exception as exc:
        output = {"status": "error", "error": str(exc), "query": query}
        append_audit("retrieve_context", {"query": query, "k": k, "caller": caller}, output, "fail", "error", start)
        return output


def confidence_from_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "Unknown"
    tier_1 = sum(1 for r in results if r.get("authority_tier") == "tier_1")
    tier_2 = sum(1 for r in results if r.get("authority_tier") == "tier_2")
    if tier_1 >= 2 and len(results) >= 3:
        return "High"
    if tier_1 >= 1 or tier_2 >= 2:
        return "Medium"
    return "Low"

"""Extend this as a team: add a new `if` branch for your own feature's
common question pattern, matching on a chunk_id prefix you own (e.g.
"order_" for Order Management)"""

def deterministic_answer(query: str, results: list[dict[str, Any]]) -> str | None:
 
    q = (query or "").lower()

    # Order Management: plain questions about orders in one status, e.g.
    # "how many orders are pending" or "which orders are shipped". Must come
    # BEFORE the generic "how many orders" check below, which would otherwise
    # return the total count instead. Only fires when every word in the
    # question is a simple status-question word; anything more specific (e.g.
    # "which pending orders contain Calendar") goes to the language model.
    order_statuses = [s for s in ("pending", "shipped", "delivered") if s in q]
    simple_words = {
        "how", "many", "which", "what", "are", "is", "the", "there", "any", "all", "of",
        "order", "orders", "status", "ids", "id", "list", "show", "me", "have", "been",
        "currently", "count", "number", "total", "do", "we", "with", "that", "in",
        "pending", "shipped", "delivered",
    }
    q_words = q.replace("?", " ").replace(".", " ").replace(",", " ").replace("!", " ").split()
    if (
        len(order_statuses) == 1
        and any(w in ("order", "orders") for w in q_words)
        and all(w in simple_words for w in q_words)
    ):
        for r in results:
            if r.get("chunk_id") == f"order_status_{order_statuses[0]}":
                return f"Answer:\n{r['text']}"

    if "how many products" in q or "product count" in q or "total products" in q:
        for r in results:
            if r.get("chunk_id") == "inventory_product_count":
                return f"Answer:\n{r['text']}"

    if ("how many orders" in q or "order count" in q) and all(w in simple_words for w in q_words):
        for r in results:
            if r.get("chunk_id") == "order_order_count":
                return f"Answer:\n{r['text']}"

    if "how many shipments" in q or "shipment count" in q:
        for r in results:
            if r.get("chunk_id") == "transport_shipment_count":
                return f"Answer:\n{r['text']}"

    if "how many storage locations" in q or "storage location count" in q:
        for r in results:
            if r.get("chunk_id") == "warehouse_location_count":
                return f"Answer:\n{r['text']}"

    return None


def generate_with_ollama(query: str, context: str) -> str:
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    ollama_generate_url = os.getenv("OLLAMA_GENERATE_URL", "http://host.docker.internal:11434/api/generate")
    prompt = f"""
You are a retrieval-grounded assistant for a supply chain management application.
Use only the provided context, which may span Order Management, Warehouse Management,
Inventory Management, and Transportation Management.
If evidence is missing, return exactly: Insufficient evidence.

QUESTION:
{query}

CONTEXT:
{context}

Return exactly:
Answer:
<answer>

Evidence:
<summary>
"""
    try:
        resp = requests.post(
            ollama_generate_url,
            json={"model": model_name, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "Insufficient evidence.")
    except Exception as exc:
        return f"Ollama unavailable: {exc}"


def answer_question(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    start = time.time()
    retrieval = retrieve_context(query=query, k=k, caller=caller)
    if retrieval.get("status") != "success":
        output = {"status": "error", "query": query, "error": retrieval.get("error", "retrieval_failed")}
        append_audit("answer_question", {"query": query, "k": k, "caller": caller}, output, "fail", "retrieval_failed", start)
        return output

    results = retrieval.get("results", [])
    context = "\n\n".join(r.get("text", "") for r in results)
    answer = deterministic_answer(query, results)
    if answer is None:
        answer = generate_with_ollama(query, context)

    citations = [
        {"chunk_id": r.get("chunk_id"), "source_id": r.get("source_id"), "authority_tier": r.get("authority_tier")}
        for r in results
    ]
    confidence = confidence_from_results(results)

    output = {
        "status": "success",
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "retrieval_summary": {"k": k, "retrieved_count": len(results), "top_chunk": results[0].get("chunk_id") if results else None},
    }
    append_audit(
        "answer_question",
        {"query": query, "k": k, "caller": caller},
        {"confidence_category": confidence, "citation_count": len(citations)},
        "pass", "answer_generated", start,
    )
    return output


if __name__ == "__main__":
    print(json.dumps(refresh_corpus(), indent=2))
    print(json.dumps(retrieve_context("which products are low on stock", 5), indent=2))
    print(json.dumps(answer_question("How many products are in inventory?", 5), indent=2))