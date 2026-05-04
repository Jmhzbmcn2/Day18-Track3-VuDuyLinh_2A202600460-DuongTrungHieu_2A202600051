"""Production RAG Pipeline — Bài tập NHÓM: ghép M1+M2+M3+M4."""

import os, sys, time

# Force UTF-8 stdout on Windows to handle Vietnamese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m1_chunking import load_documents, chunk_hierarchical
from src.m2_search import HybridSearch
from src.m3_rerank import CrossEncoderReranker, RemoteReranker
from src.m4_eval import load_test_set, evaluate_ragas, failure_analysis, save_report
from src.m5_enrichment import enrich_chunks
from config import RERANK_TOP_K, OPENROUTER_API_KEY, LLM_MODEL, LLM_BINDING_HOST, RERANKER_HOST, RERANKER_MODEL
from openai import OpenAI


def build_pipeline():
    """Build production RAG pipeline. Returns (search, reranker, latency_log)."""
    print("=" * 60)
    print("PRODUCTION RAG PIPELINE")
    print("=" * 60)
    latency_log = {}

    # Step 1: Load & Chunk (M1)
    print("\n[1/4] Chunking documents...")
    t0 = time.time()
    docs = load_documents()
    all_chunks = []
    for doc in docs:
        parents, children = chunk_hierarchical(doc["text"], metadata=doc["metadata"])
        for child in children:
            all_chunks.append({"text": child.text, "metadata": {**child.metadata, "parent_id": child.parent_id}})
    latency_log["chunking_s"] = round(time.time() - t0, 2)
    print(f"  {len(all_chunks)} chunks from {len(docs)} documents  ({latency_log['chunking_s']}s)")

    # Step 2: Enrichment (M5) — enrich first 10 chunks only to save time
    print("\n[2/4] Enriching chunks (M5 - first 10)...")
    t0 = time.time()
    subset_to_enrich = all_chunks[:10]
    remaining_chunks = all_chunks[10:]
    enriched = enrich_chunks(subset_to_enrich, methods=["contextual"])
    if enriched:
        enriched_chunks_formatted = [{"text": e.enriched_text, "metadata": e.auto_metadata} for e in enriched]
        all_chunks = enriched_chunks_formatted + remaining_chunks
        print(f"  Enriched {len(enriched)} chunks (subset)")
    else:
        print("  [!] M5 enrichment fallback - using raw chunks")
    latency_log["enrichment_s"] = round(time.time() - t0, 2)
    print(f"  Enrichment done  ({latency_log['enrichment_s']}s)")

    # Step 3: Index ALL chunks (M2) — needed to cover full test set
    print(f"\n[3/4] Indexing ALL {len(all_chunks)} chunks (BM25 + Dense)...")
    t0 = time.time()
    search = HybridSearch()
    search.index(all_chunks)
    latency_log["indexing_s"] = round(time.time() - t0, 2)
    print(f"  Indexing done  ({latency_log['indexing_s']}s)")

    # Step 4: Reranker (M3) — remote Qwen3-Reranker-0.6B via Cohere-compatible API
    print(f"\n[4/4] Connecting to remote reranker ({RERANKER_HOST})...")
    t0 = time.time()
    reranker = RemoteReranker(host=RERANKER_HOST, model=RERANKER_MODEL)
    # Quick health check
    try:
        import requests as _req
        _req.get(f"{RERANKER_HOST}/health", timeout=3)
        print(f"  Reranker ready  ({round(time.time()-t0,2)}s)")
    except Exception:
        print("  [!] Reranker health check failed — will retry per query")
    latency_log["reranker_load_s"] = round(time.time() - t0, 2)

    return search, reranker, latency_log


def run_query(query: str, search: HybridSearch, reranker) -> tuple[str, list[str]]:
    """Run single query through pipeline."""
    results = search.search(query)
    docs = [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
    reranked = reranker.rerank(query, docs, top_k=RERANK_TOP_K)
    contexts = [r.text for r in reranked] if reranked else [r.text for r in results[:3]]

    client = OpenAI(
        base_url=LLM_BINDING_HOST,
        api_key=OPENROUTER_API_KEY or "local",
    )
    context_str = "\n\n".join(contexts)
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Trả lời CHỈ dựa trên context được cung cấp. Cố gắng trả lời ngắn gọn, đầy đủ thông tin. Nếu không có thông tin trong context → nói 'Không tìm thấy.'"},
                {"role": "user", "content": f"Context:\n{context_str}\n\nCâu hỏi: {query}"},
            ]
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        answer = contexts[0] if contexts else "Không tìm thấy thông tin."
    return answer, contexts


def evaluate_pipeline(search: HybridSearch, reranker,
                      latency_log: dict | None = None):
    """Run evaluation on test set."""
    import os as _os
    _os.makedirs("reports", exist_ok=True)

    print("\n[Eval] Running queries...")
    t_gen_start = time.time()
    test_set = load_test_set()
    questions, answers, all_contexts, ground_truths = [], [], [], []

    for i, item in enumerate(test_set):
        answer, contexts = run_query(item["question"], search, reranker)
        questions.append(item["question"])
        answers.append(answer)
        all_contexts.append(contexts)
        ground_truths.append(item["ground_truth"])
        q_preview = item['question'][:50].encode('utf-8', errors='replace').decode('utf-8')
        print(f"  [{i+1}/{len(test_set)}] {q_preview}...")

    gen_s = round(time.time() - t_gen_start, 2)
    if latency_log is not None:
        latency_log["generation_s"] = gen_s
        latency_log["avg_query_s"] = round(gen_s / max(len(test_set), 1), 2)

    print("\n[Eval] Running RAGAS...")
    t_ragas = time.time()
    results = evaluate_ragas(questions, answers, all_contexts, ground_truths)
    if latency_log is not None:
        latency_log["ragas_eval_s"] = round(time.time() - t_ragas, 2)

    print("\n" + "=" * 60)
    print("PRODUCTION RAG SCORES")
    print("=" * 60)
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        s = results.get(m, 0)
        icon = '[OK]' if s >= 0.75 else '[--]'
        print(f"  {icon} {m}: {s:.4f}")

    if latency_log:
        print("\n[Latency Breakdown]")
        for k, v in latency_log.items():
            print(f"  {k}: {v}s")

    failures = failure_analysis(results.get("per_question", []))
    # Add latency to report
    results["latency"] = latency_log or {}
    save_report(results, failures, path="reports/ragas_report.json")
    return results


if __name__ == "__main__":
    start = time.time()
    search, reranker, latency_log = build_pipeline()
    evaluate_pipeline(search, reranker, latency_log)
    print(f"\nTotal: {time.time() - start:.1f}s")
