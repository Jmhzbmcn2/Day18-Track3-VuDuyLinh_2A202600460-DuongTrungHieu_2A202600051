"""Module 2: Hybrid Search — BM25 (Vietnamese) + Dense + RRF."""

import os, sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, EMBEDDING_MODEL,
                    EMBEDDING_DIM, BM25_TOP_K, DENSE_TOP_K, HYBRID_TOP_K)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str  # "bm25", "dense", "hybrid"


def segment_vietnamese(text: str) -> str:
    """Segment Vietnamese text into words."""
    try:
        from underthesea import word_tokenize
        return word_tokenize(text, format="text")
    except ImportError:
        return text


class BM25Search:
    def __init__(self):
        self.corpus_tokens = []
        self.documents = []
        self.bm25 = None

    def index(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunks."""
        self.documents = chunks
        self.corpus_tokens = []
        for chunk in chunks:
            tokenized = segment_vietnamese(chunk.get("text", "")).split()
            self.corpus_tokens.append(tokenized)
            
        from rank_bm25 import BM25Okapi
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        """Search using BM25."""
        if not self.bm25 or not self.documents:
            return []
        tokenized_query = segment_vietnamese(query).split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for i in top_indices:
            doc = self.documents[i]
            results.append(SearchResult(
                text=doc.get("text", ""),
                score=float(scores[i]),
                metadata=doc.get("metadata", {}),
                method="bm25"
            ))
        return results


class DenseSearch:
    def __init__(self):
        from qdrant_client import QdrantClient
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(EMBEDDING_MODEL)
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        """Index chunks into Qdrant."""
        from qdrant_client.models import Distance, VectorParams, PointStruct
        self.client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        vectors = self._get_encoder().encode(texts, show_progress_bar=True)
        
        points = []
        for i, (v, c) in enumerate(zip(vectors, chunks)):
            points.append(PointStruct(
                id=i,
                vector=v.tolist(),
                payload={**c.get("metadata", {}), "text": c.get("text", "")}
            ))
            
        self.client.upsert(collection_name=collection, points=points)

    def search(self, query: str, top_k: int = DENSE_TOP_K, collection: str = COLLECTION_NAME) -> list[SearchResult]:
        """Search using dense vectors."""
        query_vector = self._get_encoder().encode(query).tolist()
        hits = self.client.search(collection_name=collection, query_vector=query_vector, limit=top_k)
        
        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(SearchResult(
                text=payload.get("text", ""),
                score=float(hit.score),
                metadata=payload,
                method="dense"
            ))
        return results


def reciprocal_rank_fusion(results_list: list[list[SearchResult]], k: int = 60,
                           top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
    """Merge ranked lists using RRF: score(d) = Σ 1/(k + rank)."""
    rrf_scores = {}  # text → {"score": float, "result": SearchResult}
    
    for r_list in results_list:
        for rank, res in enumerate(r_list):
            if res.text not in rrf_scores:
                rrf_scores[res.text] = {
                    "score": 0.0,
                    "result": res
                }
            rrf_scores[res.text]["score"] += 1.0 / (k + rank + 1)
            
    sorted_texts = sorted(rrf_scores.keys(), key=lambda t: rrf_scores[t]["score"], reverse=True)[:top_k]
    
    merged = []
    for text in sorted_texts:
        res = rrf_scores[text]["result"]
        merged.append(SearchResult(
            text=res.text,
            score=rrf_scores[text]["score"],
            metadata=res.metadata,
            method="hybrid"
        ))
        
    return merged


class HybridSearch:
    """Combines BM25 + Dense + RRF. (Đã implement sẵn — dùng classes ở trên)"""
    def __init__(self):
        self.bm25 = BM25Search()
        self.dense = DenseSearch()

    def index(self, chunks: list[dict]) -> None:
        self.bm25.index(chunks)
        self.dense.index(chunks)

    def search(self, query: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        dense_results = self.dense.search(query, top_k=DENSE_TOP_K)
        return reciprocal_rank_fusion([bm25_results, dense_results], top_k=top_k)


if __name__ == "__main__":
    print(f"Original:  Nhân viên được nghỉ phép năm")
    print(f"Segmented: {segment_vietnamese('Nhân viên được nghỉ phép năm')}")
