"""
Module 5: Enrichment Pipeline
==============================
Làm giàu chunks TRƯỚC khi embed: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import os, sys
import json
from dataclasses import dataclass, field
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENROUTER_API_KEY, LLM_MODEL, LLM_BINDING_HOST

# Initialize local LLM client (OpenAI-compatible)
client = OpenAI(
    base_url=LLM_BINDING_HOST,
    api_key=OPENROUTER_API_KEY or "local",
)

@dataclass
class EnrichedChunk:
    """Chunk đã được làm giàu."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


# ─── Technique 1: Chunk Summarization ────────────────────


def summarize_chunk(text: str) -> str:
    """
    Tạo summary ngắn cho chunk.
    Embed summary thay vì (hoặc cùng với) raw chunk → giảm noise.
    """
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Tóm tắt đoạn văn sau trong 2-3 câu ngắn gọn bằng tiếng Việt."},
                {"role": "user", "content": text},
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in summarize_chunk: {e}")
        sentences = text.split(". ")
        return ". ".join(sentences[:2]) + "."


# ─── Technique 2: Hypothesis Question-Answer (HyQA) ─────


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """
    Generate câu hỏi mà chunk có thể trả lời.
    Index cả questions lẫn chunk → query match tốt hơn (bridge vocabulary gap).
    """
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": f"Dựa trên đoạn văn, tạo {n_questions} câu hỏi mà đoạn văn có thể trả lời. Trả về mỗi câu hỏi trên 1 dòng. Không bao gồm số thứ tự ở đầu."},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
        )
        questions = resp.choices[0].message.content.strip().split("\n")
        return [q.strip().lstrip("0123456789.-) ") for q in questions if q.strip()]
    except Exception as e:
        print(f"Error in generate_hypothesis_questions: {e}")
        return []


# ─── Technique 3: Contextual Prepend (Anthropic style) ──


def contextual_prepend(text: str, document_title: str = "") -> str:
    """
    Prepend context giải thích chunk nằm ở đâu trong document.
    Anthropic benchmark: giảm 49% retrieval failure (alone).
    """
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Viết 1 câu ngắn mô tả đoạn văn này nằm ở đâu trong tài liệu và nói về chủ đề gì. Chỉ trả về 1 câu."},
                {"role": "user", "content": f"Tài liệu: {document_title}\n\nĐoạn văn:\n{text}"},
            ],
            max_tokens=80,
        )
        context = resp.choices[0].message.content.strip()
        return f"{context}\n\n{text}"
    except Exception as e:
        print(f"Error in contextual_prepend: {e}")
        return f"{document_title}\n\n{text}" if document_title else text


# ─── Technique 4: Auto Metadata Extraction ──────────────


def extract_metadata(text: str) -> dict:
    """
    LLM extract metadata tự động: topic, entities, date_range, category.
    """
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": 'Trích xuất metadata từ đoạn văn. Trả về đúng định dạng JSON hợp lệ: {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance|other", "language": "vi|en"}'},
                {"role": "user", "content": text},
            ],
            response_format={ "type": "json_object" },
            max_tokens=150,
        )
        # Parse JSON
        content = resp.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error in extract_metadata: {e}")
        return {}


# ─── Full Enrichment Pipeline ────────────────────────────


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    """
    Chạy enrichment pipeline trên danh sách chunks.
    """
    if methods is None:
        methods = ["contextual", "hyqa", "metadata"]

    enriched = []

    for i, chunk in enumerate(chunks):
        print(f"Enriching chunk {i+1}/{len(chunks)}...")
        text = chunk["text"]
        meta = chunk.get("metadata", {})
        source = meta.get("source", "")
        
        summary = ""
        questions = []
        enriched_text = text
        auto_meta = {}
        
        if "summary" in methods or "full" in methods:
            summary = summarize_chunk(text)
            
        if "hyqa" in methods or "full" in methods:
            questions = generate_hypothesis_questions(text)
            
        if "contextual" in methods or "full" in methods:
            enriched_text = contextual_prepend(text, source)
            
        if "metadata" in methods or "full" in methods:
            auto_meta = extract_metadata(text)
            
        final_meta = {**meta, **auto_meta}
        
        enriched.append(EnrichedChunk(
            original_text=text,
            enriched_text=enriched_text,
            summary=summary,
            hypothesis_questions=questions,
            auto_metadata=final_meta,
            method="+".join(methods),
        ))

    return enriched


# ─── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm. Số ngày nghỉ phép tăng thêm 1 ngày cho mỗi 5 năm thâm niên công tác."

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {sample}\n")

    s = summarize_chunk(sample)
    print(f"Summary: {s}\n")

    qs = generate_hypothesis_questions(sample)
    print(f"HyQA questions: {qs}\n")

    ctx = contextual_prepend(sample, "Sổ tay nhân viên VinUni 2024")
    print(f"Contextual: {ctx}\n")

    meta = extract_metadata(sample)
    print(f"Auto metadata: {meta}")
