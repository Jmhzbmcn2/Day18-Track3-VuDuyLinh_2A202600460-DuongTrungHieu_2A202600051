"""
Module 1: Advanced Chunking Strategies
=======================================
Implement semantic, hierarchical, và structure-aware chunking.
So sánh với basic chunking (baseline) để thấy improvement.

Test: pytest tests/test_m1.py
"""

import os, sys, glob, re
from dataclasses import dataclass, field
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_DIR, HIERARCHICAL_PARENT_SIZE, HIERARCHICAL_CHILD_SIZE,
                    SEMANTIC_THRESHOLD)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    parent_id: str | None = None


def load_documents(data_dir: str = DATA_DIR) -> list[dict]:
    """Load all markdown/text files from data/. (Đã implement sẵn)"""
    docs = []
    for fp in sorted(glob.glob(os.path.join(data_dir, "*.md"))):
        with open(fp, encoding="utf-8") as f:
            docs.append({"text": f.read(), "metadata": {"source": os.path.basename(fp)}})
    return docs


# ─── Baseline: Basic Chunking (để so sánh) ──────────────


def chunk_basic(text: str, chunk_size: int = 500, metadata: dict | None = None) -> list[Chunk]:
    """
    Basic chunking: split theo paragraph (\\n\\n).
    Đây là baseline — KHÔNG phải mục tiêu của module này.
    (Đã implement sẵn)
    """
    metadata = metadata or {}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for i, para in enumerate(paragraphs):
        if len(current) + len(para) > chunk_size and current:
            chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
            current = ""
        current += para + "\n\n"
    if current.strip():
        chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
    return chunks


# ─── Strategy 1: Semantic Chunking ───────────────────────


def chunk_semantic(text: str, threshold: float = SEMANTIC_THRESHOLD,
                   metadata: dict | None = None) -> list[Chunk]:
    """
    Split text by sentence similarity — nhóm câu cùng chủ đề.
    Tốt hơn basic vì không cắt giữa ý.

    Args:
        text: Input text.
        threshold: Cosine similarity threshold. Dưới threshold → tách chunk mới.
        metadata: Metadata gắn vào mỗi chunk.

    Returns:
        List of Chunk objects grouped by semantic similarity.
    """
    metadata = metadata or {}
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n\n', text) if s.strip()]
    if not sentences:
        return []

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(sentences)

    from numpy import dot
    from numpy.linalg import norm
    def cosine_sim(a, b):
        denom = norm(a) * norm(b)
        if denom == 0:
            return 0.0
        return dot(a, b) / denom

    chunks = []
    current_group = [sentences[0]]
    for i in range(1, len(sentences)):
        sim = cosine_sim(embeddings[i-1], embeddings[i])
        if sim < threshold:
            chunks.append(Chunk(text=" ".join(current_group), metadata={**metadata, "chunk_index": len(chunks), "strategy": "semantic"}))
            current_group = []
        current_group.append(sentences[i])
    
    if current_group:
        chunks.append(Chunk(text=" ".join(current_group), metadata={**metadata, "chunk_index": len(chunks), "strategy": "semantic"}))

    return chunks


# ─── Strategy 2: Hierarchical Chunking ──────────────────


def chunk_hierarchical(text: str, parent_size: int = HIERARCHICAL_PARENT_SIZE,
                       child_size: int = HIERARCHICAL_CHILD_SIZE,
                       metadata: dict | None = None) -> tuple[list[Chunk], list[Chunk]]:
    """
    Parent-child hierarchy: retrieve child (precision) → return parent (context).
    Đây là default recommendation cho production RAG.

    Args:
        text: Input text.
        parent_size: Chars per parent chunk.
        child_size: Chars per child chunk.
        metadata: Metadata gắn vào mỗi chunk.

    Returns:
        (parents, children) — mỗi child có parent_id link đến parent.
    """
    metadata = metadata or {}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    parent_texts = []
    current_parent_text = ""
    for para in paragraphs:
        if len(current_parent_text) + len(para) + 2 > parent_size and current_parent_text:
            parent_texts.append(current_parent_text.strip())
            current_parent_text = para + "\n\n"
        else:
            if current_parent_text:
                current_parent_text += para + "\n\n"
            else:
                current_parent_text = para + "\n\n"
    if current_parent_text.strip():
        parent_texts.append(current_parent_text.strip())
        
    if not parent_texts and text.strip():
        parent_texts.append(text.strip())

    parents_list = []
    children_list = []
    
    for p_index, p_text in enumerate(parent_texts):
        pid = f"parent_{p_index}"
        parent_chunk = Chunk(text=p_text, metadata={**metadata, "chunk_type": "parent", "parent_id": pid})
        parents_list.append(parent_chunk)
        
        for start in range(0, len(p_text), child_size):
            c_text = p_text[start:start+child_size]
            if c_text.strip():
                child_chunk = Chunk(
                    text=c_text.strip(),
                    metadata={**metadata, "chunk_type": "child"},
                    parent_id=pid
                )
                children_list.append(child_chunk)
                
    return parents_list, children_list


# ─── Strategy 3: Structure-Aware Chunking ────────────────


def chunk_structure_aware(text: str, metadata: dict | None = None) -> list[Chunk]:
    """
    Parse markdown headers → chunk theo logical structure.
    Giữ nguyên tables, code blocks, lists — không cắt giữa chừng.

    Args:
        text: Markdown text.
        metadata: Metadata gắn vào mỗi chunk.

    Returns:
        List of Chunk objects, mỗi chunk = 1 section (header + content).
    """
    metadata = metadata or {}
    sections = re.split(r'(^#{1,3}\s+.+$)', text, flags=re.MULTILINE)
    
    chunks = []
    current_header = ""
    current_content = ""
    for part in sections:
        if part is None:
            continue
        if re.match(r'^#{1,3}\s+', part):
            if current_header or current_content.strip():
                chunk_text = f"{current_header}\n{current_content}".strip()
                if chunk_text:
                    chunks.append(Chunk(
                        text=chunk_text,
                        metadata={**metadata, "section": current_header, "strategy": "structure"}
                    ))
            current_header = part.strip()
            current_content = ""
        else:
            current_content += part
            
    chunk_text = f"{current_header}\n{current_content}".strip()
    if chunk_text:
        chunks.append(Chunk(
            text=chunk_text,
            metadata={**metadata, "section": current_header, "strategy": "structure"}
        ))
        
    return chunks


# ─── A/B Test: Compare All Strategies ────────────────────


def compare_strategies(documents: list[dict]) -> dict:
    """
    Run all strategies on documents and compare.

    Returns:
        {"basic": {...}, "semantic": {...}, "hierarchical": {...}, "structure": {...}}
    """
    results = {
        "basic": {"num_chunks": 0, "avg_length": 0.0, "min_length": float('inf'), "max_length": 0},
        "semantic": {"num_chunks": 0, "avg_length": 0.0, "min_length": float('inf'), "max_length": 0},
        "hierarchical": {"num_chunks": 0, "avg_length": 0.0, "min_length": float('inf'), "max_length": 0},
        "structure": {"num_chunks": 0, "avg_length": 0.0, "min_length": float('inf'), "max_length": 0},
    }
    
    strategy_chunks = {
        "basic": [],
        "semantic": [],
        "hierarchical": [],
        "structure": []
    }
    
    for doc in documents:
        text = doc.get("text", "")
        meta = doc.get("metadata", {})
        
        strategy_chunks["basic"].extend(chunk_basic(text, metadata=meta))
        strategy_chunks["semantic"].extend(chunk_semantic(text, metadata=meta))
        
        p, c = chunk_hierarchical(text, metadata=meta)
        strategy_chunks["hierarchical"].extend(p + c)
        
        strategy_chunks["structure"].extend(chunk_structure_aware(text, metadata=meta))
        
    for strat, chunks in strategy_chunks.items():
        if chunks:
            lengths = [len(chunk.text) for chunk in chunks]
            results[strat]["num_chunks"] = len(chunks)
            results[strat]["avg_length"] = sum(lengths) / len(chunks)
            results[strat]["min_length"] = min(lengths)
            results[strat]["max_length"] = max(lengths)
        else:
            results[strat]["num_chunks"] = 0
            results[strat]["avg_length"] = 0.0
            results[strat]["min_length"] = 0
            results[strat]["max_length"] = 0
            
    print(f"{'Strategy':<14} | {'Chunks':<6} | {'Avg Len':<7} | {'Min':<5} | {'Max':<5}")
    print("-" * 50)
    for name, stats in results.items():
        print(f"{name:<14} | {stats['num_chunks']:<6} | {stats['avg_length']:<7.1f} | {stats['min_length']:<5} | {stats['max_length']:<5}")
        
    return results


if __name__ == "__main__":
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")
    results = compare_strategies(docs)
    for name, stats in results.items():
        print(f"  {name}: {stats}")
