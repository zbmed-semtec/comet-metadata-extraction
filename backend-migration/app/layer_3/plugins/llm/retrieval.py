from __future__ import annotations

import re

from app.layer_3.plugins.llm.config import PROPERTY_QUERIES

try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None

try:
    import numpy as np  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    np = None


def split_with_metadata(md_text: str) -> list[dict]:
    """Split Markdown into sections while retaining heading metadata."""
    lines = md_text.split("\n")
    chunks = []
    current = {"heading": None, "level": None, "content": []}

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if current["content"]:
                chunks.append(current)
            current = {"heading": m.group(2), "level": len(m.group(1)), "content": []}
            i += 1
            continue

        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.match(r"^=+$", next_line):
                if current["content"]:
                    chunks.append(current)
                current = {"heading": line, "level": 1, "content": []}
                i += 2
                continue
            if re.match(r"^-+$", next_line):
                if current["content"]:
                    chunks.append(current)
                current = {"heading": line, "level": 2, "content": []}
                i += 2
                continue

        current["content"].append(lines[i])
        i += 1

    if current["content"]:
        chunks.append(current)

    return chunks


def hybrid_chunking(section: dict, max_chars: int = 1200, overlap: int = 200) -> list[dict]:
    """Break a Markdown section into overlapping, size-limited chunks."""
    text = "\n".join(section["content"]).strip()
    if len(text) <= max_chars:
        return [{"heading": section["heading"], "content": text}]

    out = []
    start = 0
    while start < len(text):
        end = start + max_chars
        out.append({"heading": section["heading"], "content": text[start:end]})
        start += max_chars - overlap
    return out


def prepare_chunk_records(chunks: list[dict]) -> list[dict]:
    """Normalize chunks into records ready for keyword or vector retrieval."""
    records = []
    for i, chunk in enumerate(chunks):
        heading = "" if chunk.get("heading") is None else str(chunk.get("heading")).strip()
        content = "" if chunk.get("content") is None else str(chunk.get("content")).strip()
        if not content:
            continue
        records.append(
            {
                "chunk_id": i,
                "heading": heading,
                "content": content,
                "full_text": f"Heading: {heading}\n\n{content}" if heading else content,
            }
        )
    return records


def build_retrieval_index(records: list[dict], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> dict:
    """Build a retrieval index, adding embeddings when available."""
    index = {
        "records": records,
        "embeddings": None,
        "model": None,
        "embedding_enabled": False,
    }

    if SentenceTransformer is None:
        return index

    try:
        model = SentenceTransformer(model_name)
        vec = model.encode([record["full_text"] for record in records], normalize_embeddings=True)
        if np is not None:
            index["embeddings"] = np.asarray(vec, dtype=np.float32)
        else:
            index["embeddings"] = [list(map(float, row)) for row in vec]
        index["model"] = model
        index["embedding_enabled"] = True
    except Exception:
        pass

    return index


def keyword_score(record: dict, query_terms: list[str]) -> float:
    """Score one record by occurrences of property-related query terms."""
    heading = record["heading"].lower()
    content = record["content"].lower()
    score = 0.0
    for term in query_terms:
        normalized = term.lower()
        if normalized in heading:
            score += 2.0
        if normalized in content:
            score += 1.0
    return score


def retrieve_top_chunks(index: dict, property_name: str, top_k: int = 5, alpha: float = 0.75) -> list[dict]:
    """Rank and return README chunks most relevant to a metadata property."""
    terms = PROPERTY_QUERIES.get(property_name, [property_name])
    records = index["records"]

    kw = [float(keyword_score(record, terms)) for record in records]
    if kw and max(kw) > 0:
        max_kw = max(kw)
        kw = [score / max_kw for score in kw]

    if index["embedding_enabled"] and records:
        query_text = " ".join(terms)
        query_vector = index["model"].encode([query_text], normalize_embeddings=True)[0]
        if hasattr(query_vector, "tolist"):
            query_vector = query_vector.tolist()

        if np is not None and hasattr(index["embeddings"], "__matmul__"):
            sem_values = index["embeddings"] @ np.asarray(query_vector, dtype=np.float32)
            sem = [float((value + 1.0) / 2.0) for value in sem_values]
        else:
            sem = []
            for row in index["embeddings"]:
                dot = sum(float(left) * float(right) for left, right in zip(row, query_vector))
                sem.append((dot + 1.0) / 2.0)

        scores = [alpha * sem_value + (1 - alpha) * kw_value for sem_value, kw_value in zip(sem, kw)]
    else:
        scores = kw

    order = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:top_k]
    out = []
    for rank, idx in enumerate(order, start=1):
        record = dict(records[int(idx)])
        record["score"] = float(scores[int(idx)])
        record["rank"] = rank
        out.append(record)
    return out
