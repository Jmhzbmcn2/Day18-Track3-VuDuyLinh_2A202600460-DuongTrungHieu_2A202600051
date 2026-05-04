"""Module 3: Reranking — Cross-encoder top-20 → top-3 + latency benchmark."""

import os, sys, time
from dataclasses import dataclass
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_TOP_K, RERANKER_HOST, RERANKER_MODEL


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, device="cpu")
        return self._model

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        """Rerank documents: top-20 → top-k."""
        if not documents:
            return []
            
        model = self._load_model()
        pairs = [(query, doc["text"]) for doc in documents]
        scores = model.predict(pairs)
        
        results = []
        for i, (score, doc) in enumerate(zip(scores, documents)):
            results.append({
                "doc": doc,
                "score": float(score)
            })
            
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top_k
        final_results = []
        for i, item in enumerate(results[:top_k]):
            final_results.append(RerankResult(
                text=item["doc"]["text"],
                original_score=item["doc"].get("score", 0.0),
                rerank_score=item["score"],
                metadata=item["doc"].get("metadata", {}),
                rank=i + 1
            ))
            
        return final_results


class RemoteReranker:
    """Reranker via Cohere-compatible API (e.g. Qwen3-Reranker-0.6B hosted on vLLM)."""

    def __init__(self, host: str = RERANKER_HOST, model: str = RERANKER_MODEL):
        self.host = host.rstrip("/")
        self.model = model

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        if not documents:
            return []
        doc_texts = [doc.get("text", "") for doc in documents]
        payload = {"query": query, "documents": doc_texts, "top_n": top_k}
        resp = requests.post(f"{self.host}/rerank", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for i, item in enumerate(data["results"]):
            idx = item["index"]
            doc = documents[idx]
            results.append(RerankResult(
                text=doc.get("text", ""),
                original_score=float(doc.get("score", 0.0)),
                rerank_score=float(item["relevance_score"]),
                metadata=doc.get("metadata", {}),
                rank=i + 1,
            ))
        return results


class FlashrankReranker:
    """Lightweight alternative (<5ms). Optional."""
    def __init__(self):
        self._model = None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        # TODO (optional): from flashrank import Ranker, RerankRequest
        # model = Ranker(); passages = [{"text": d["text"]} for d in documents]
        # results = model.rerank(RerankRequest(query=query, passages=passages))
        return []


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Benchmark latency over n_runs."""
    times = []
    # Warmup
    reranker.rerank(query, documents)
    
    for _ in range(n_runs):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        times.append((time.perf_counter() - start) * 1000)  # ms
        
    return {
        "avg_ms": sum(times) / len(times) if times else 0,
        "min_ms": min(times) if times else 0,
        "max_ms": max(times) if times else 0
    }


if __name__ == "__main__":
    query = "Nhân viên được nghỉ phép bao nhiêu ngày?"
    docs = [
        {"text": "Nhân viên được nghỉ 12 ngày/năm.", "score": 0.8, "metadata": {}},
        {"text": "Mật khẩu thay đổi mỗi 90 ngày.", "score": 0.7, "metadata": {}},
        {"text": "Thời gian thử việc là 60 ngày.", "score": 0.75, "metadata": {}},
    ]
    reranker = CrossEncoderReranker()
    for r in reranker.rerank(query, docs):
        print(f"[{r.rank}] {r.rerank_score:.4f} | {r.text}")
