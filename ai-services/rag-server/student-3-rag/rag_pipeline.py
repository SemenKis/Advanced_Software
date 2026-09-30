import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import requests

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
REPORTS_DIR = APP_DIR / "docs" / "reports"
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
AUDIT_PATH = BASE_DIR / "rag-audit.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5023")

REPORT_FILES = ["report.json", "run-view.md", "run-report.md"]

COLLECTION_NAME = "inventory_management_enterprise_context"
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


def chunk_text(text: str, max_words: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i:i + max_words]).strip() for i in range(0, len(words), max_words) if words[i:i + max_words]]


def load_database_chunks() -> list[dict[str, Any]]:
    """Chunk one fact per product, plus category/supplier/stocktake summaries."""
    chunks: list[dict[str, Any]] = []
    try:
        products = requests.get(f"{DATABASE_SERVICE_URL}/products", timeout=10).json()
        low_stock = requests.get(f"{DATABASE_SERVICE_URL}/products/low-stock", timeout=10).json()
        stocktakes = requests.get(f"{DATABASE_SERVICE_URL}/stocktakes", timeout=10).json()
    except Exception as exc:
        return [{
            "chunk_id": "db_unreachable",
            "source_id": "database-service",
            "authority_tier": "tier_1",
            "text": f"Database service unreachable: {exc}",
            "metadata": {"source_type": "database", "reachable": False},
            "indexed_at": now_iso(),
        }]

    chunks.append({
        "chunk_id": "db_product_count",
        "source_id": "database-service:/products",
        "authority_tier": "tier_1",
        "text": f"Total product count in inventory is {len(products)}.",
        "metadata": {"source_type": "database", "metric": "count"},
        "indexed_at": now_iso(),
    })

    for p in products:
        chunks.append({
            "chunk_id": f"db_product_{p['product_id']}",
            "source_id": "database-service:/products",
            "authority_tier": "tier_1",
            "text": (
                f"Product record: name={p['name']}, brand={p.get('brand') or 'n/a'}, "
                f"category={p['category_name']}, supplier={p['supplier_name']}, "
                f"price={p['price']}, quantity={p['quantity']}, reorder_level={p['reorder_level']}."
            ),
            "metadata": {"source_type": "database", "table": "products"},
            "indexed_at": now_iso(),
        })

    if low_stock:
        low_stock_text = "; ".join(
            f"{p['name']} (qty {p['quantity']}, reorder level {p['reorder_level']}, supplier {p['supplier_name']})"
            for p in low_stock
        )
        chunks.append({
            "chunk_id": "db_low_stock_summary",
            "source_id": "database-service:/products/low-stock",
            "authority_tier": "tier_1",
            "text": f"Products currently at or below their reorder level: {low_stock_text}.",
            "metadata": {"source_type": "database", "metric": "low_stock"},
            "indexed_at": now_iso(),
        })
    else:
        chunks.append({
            "chunk_id": "db_low_stock_summary",
            "source_id": "database-service:/products/low-stock",
            "authority_tier": "tier_1",
            "text": "No products are currently at or below their reorder level.",
            "metadata": {"source_type": "database", "metric": "low_stock"},
            "indexed_at": now_iso(),
        })

    for s in stocktakes[:50]:
        chunks.append({
            "chunk_id": f"db_stocktake_{s['stocktake_id']}",
            "source_id": "database-service:/stocktakes",
            "authority_tier": "tier_1",
            "text": (
                f"Stocktake record: product={s['product_name']}, counted_by={s['member_name']}, "
                f"counted_quantity={s['counted_quantity']}, timestamp={s['timestamp']}."
            ),
            "metadata": {"source_type": "database", "table": "stocktake"},
            "indexed_at": now_iso(),
        })

    return chunks


def load_report_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    if not REPORTS_DIR.exists():
        return chunks
    for name in REPORT_FILES:
        path = REPORTS_DIR / name
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, chunk in enumerate(chunk_text(text), start=1):
            chunks.append({
                "chunk_id": f"{path.stem}_{i}",
                "source_id": f"docs/reports/{name}",
                "authority_tier": "tier_2",
                "text": chunk,
                "metadata": {"source_type": "report", "file": name},
                "indexed_at": now_iso(),
            })
    return chunks


def load_repository_chunks() -> list[dict[str, Any]]:
    ignored = {".git", ".venv", "__pycache__", "node_modules", "chroma"}
    files: list[str] = []
    for root, dirs, filenames in os.walk(APP_DIR, topdown=True, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if d not in ignored]
        for filename in filenames:
            try:
                files.append(str((Path(root) / filename).relative_to(APP_DIR)))
            except ValueError:
                continue
    text = "Inventory feature repository files include: " + ", ".join(sorted(files[:300]))
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
    chunks.extend(load_database_chunks())
    chunks.extend(load_report_chunks())
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

        output = {
            "status": "success",
            "caller": caller,
            "chunk_count": len(chunks),
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


def deterministic_answer(query: str, results: list[dict[str, Any]]) -> str | None:
    """Answer common inventory questions directly from retrieved facts, skipping the LLM
    entirely when the evidence already contains an exact, unambiguous answer."""
    q = (query or "").lower()

    if "how many products" in q or "product count" in q or "total products" in q:
        for r in results:
            if r.get("chunk_id") == "db_product_count":
                return f"Answer:\n{r['text']}"

    if "low stock" in q or ("low" in q and "stock" in q) or "reorder" in q:
        for r in results:
            if r.get("chunk_id") == "db_low_stock_summary":
                return f"Answer:\n{r['text']}"

    return None


def generate_with_ollama(query: str, context: str) -> str:
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    ollama_generate_url = os.getenv("OLLAMA_GENERATE_URL", "http://host.docker.internal:11434/api/generate")
    prompt = f"""
You are a retrieval-grounded inventory assistant.
Use only the provided context.
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
