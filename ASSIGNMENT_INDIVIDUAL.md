# Phần A: Bài tập cá nhân — Implement 1 Module

**Thời gian:** 1.5 giờ · **Điểm:** 60/100

---

## Hướng dẫn

1. Nhóm 4–5 người → mỗi người chọn **1 module khác nhau**
2. Nhóm 3 người → 1 người làm M5 kèm M1 hoặc M4
3. Làm 1 mình → chọn M1 hoặc M2 (core nhất)
4. Mở file `src/m*_<tên>.py` → tìm `# TODO:` → implement
5. Chạy `pytest tests/test_m*.py` để kiểm tra

---

## Module 1: Advanced Chunking Strategies

**File:** `src/m1_chunking.py` · **Test:** `pytest tests/test_m1.py`

### Yêu cầu
Implement 3 advanced chunking strategies và so sánh A/B với basic baseline:

| Strategy | Hàm | Mô tả |
|----------|-----|-------|
| Baseline (có sẵn) | `chunk_basic()` | Split theo paragraph — đã implement, dùng để so sánh |
| Semantic | `chunk_semantic()` | Nhóm câu theo cosine similarity — không cắt giữa ý |
| Hierarchical | `chunk_hierarchical()` | Parent (2048) + Child (256), retrieve child → return parent |
| Structure-Aware | `chunk_structure_aware()` | Parse markdown headers → chunk theo section logic |

### TODO trong code
```python
# TODO 1: chunk_semantic() — encode sentences, split khi similarity < threshold
# TODO 2: chunk_hierarchical() — parent chunks → split thành children, gán parent_id
# TODO 3: chunk_structure_aware() — regex split markdown headers, pair header + content
# TODO 4: compare_strategies() — chạy cả 4, in bảng so sánh
```

### Test pass criteria
- [ ] Semantic: trả về `list[Chunk]` không rỗng, nhóm theo topic
- [ ] Hierarchical: mỗi child có `parent_id` hợp lệ, children nhỏ hơn parents
- [ ] Structure-Aware: giữ nguyên headers, có `section` trong metadata
- [ ] `compare_strategies()` trả về stats cho cả 4 strategies

---

## Module 2: Hybrid Search

**File:** `src/m2_search.py` · **Test:** `pytest tests/test_m2.py`

### Yêu cầu
Implement BM25 (Vietnamese) + Dense vector + RRF fusion:

| Component | Class/Hàm | Mô tả |
|-----------|-----------|-------|
| Vietnamese segmentation | `segment_vietnamese()` | underthesea word_tokenize |
| BM25 | `BM25Search.index()` + `.search()` | BM25Okapi trên text đã segment |
| Dense | `DenseSearch.index()` + `.search()` | bge-m3 + Qdrant |
| RRF | `reciprocal_rank_fusion()` | score(d) = Σ 1/(k + rank_i(d)) |

### TODO trong code
```python
# TODO 1: segment_vietnamese() — underthesea.word_tokenize(text, format="text")
# TODO 2: BM25Search.index() — segment → tokenize → BM25Okapi
# TODO 3: BM25Search.search() — segment query → get_scores → top-k
# TODO 4: DenseSearch.index() — encode → upload PointStruct to Qdrant
# TODO 5: DenseSearch.search() — encode query → client.search()
# TODO 6: reciprocal_rank_fusion() — merge rankings, score = Σ 1/(k+rank)
```

### Test pass criteria
- [ ] `segment_vietnamese()` trả về string khác rỗng
- [ ] BM25 search trả về results với `method="bm25"`
- [ ] RRF merge 2 lists → results với `method="hybrid"`
- [ ] Query "nghỉ phép" → kết quả đầu tiên chứa "nghỉ phép"

---

## Module 3: Reranking

**File:** `src/m3_rerank.py` · **Test:** `pytest tests/test_m3.py`

### Yêu cầu
Integrate cross-encoder reranker, benchmark latency:

| Component | Class/Hàm | Mô tả |
|-----------|-----------|-------|
| Cross-encoder | `CrossEncoderReranker.rerank()` | bge-reranker-v2-m3 |
| Flashrank | `FlashrankReranker.rerank()` | Lightweight alternative |
| Benchmark | `benchmark_reranker()` | Đo avg/min/max latency |

### TODO trong code
```python
# TODO 1: CrossEncoderReranker._load_model() — load FlagReranker hoặc CrossEncoder
# TODO 2: CrossEncoderReranker.rerank() — predict scores → sort → top-k
# TODO 3: FlashrankReranker (optional) — Ranker().rerank()
# TODO 4: benchmark_reranker() — time.perf_counter() × n_runs → stats
```

### Test pass criteria
- [ ] Rerank 5 docs → trả về ≤ 3 `RerankResult`
- [ ] Results sorted by `rerank_score` descending
- [ ] Doc về "nghỉ phép" ranked cao hơn doc về "VPN"
- [ ] Latency < 5 giây (first load chậm OK)

---

## Module 4: RAGAS Evaluation

**File:** `src/m4_eval.py` · **Test:** `pytest tests/test_m4.py`

### Yêu cầu
RAGAS evaluation pipeline + failure analysis:

| Component | Hàm | Mô tả |
|-----------|-----|-------|
| Evaluate | `evaluate_ragas()` | 4 metrics: F, AR, CP, CR |
| Failure analysis | `failure_analysis()` | Bottom-10, map vào Diagnostic Tree |
| Report | `save_report()` | JSON output |

### TODO trong code
```python
# TODO 1: evaluate_ragas() — Dataset.from_dict → ragas.evaluate → extract scores
# TODO 2: failure_analysis() — sort by avg score → bottom-N → diagnose worst metric
# TODO 3: Diagnostic mapping:
#          faithfulness < 0.85 → "LLM hallucinating" → "Tighten prompt"
#          context_recall < 0.75 → "Missing chunks" → "Improve chunking/search"
#          context_precision < 0.75 → "Irrelevant chunks" → "Add reranking"
#          answer_relevancy < 0.80 → "Answer mismatch" → "Improve prompt"
```

### Test pass criteria
- [ ] `evaluate_ragas()` trả về dict với 4 metric keys
- [ ] Scores là numeric (int hoặc float)
- [ ] `failure_analysis()` trả về list với `diagnosis` và `suggested_fix`
- [ ] `load_test_set()` load được 20 questions

---

## Chấm điểm cá nhân (60 điểm)

| Tiêu chí | Điểm |
|----------|------|
| Module implementation đúng logic | 15 |
| `pytest tests/test_m*.py` pass | 15 |
| Vietnamese-specific handling (segment, bge-m3, ...) | 10 |
| Code quality: comments, type hints, clean | 10 |
| Tất cả TODO markers hoàn thành | 10 |
| **Tổng cá nhân** | **60** |


---

## Module 5: Enrichment Pipeline

**File:** `src/m5_enrichment.py` · **Test:** `pytest tests/test_m5.py`

### Yêu cầu
Làm giàu chunks trước khi embed — 4 techniques:

| Technique | Hàm | Mô tả |
|-----------|-----|-------|
| Summarize | `summarize_chunk()` | LLM tóm tắt chunk → giảm noise |
| HyQA | `generate_hypothesis_questions()` | Generate câu hỏi chunk có thể trả lời → bridge vocabulary gap |
| Contextual Prepend | `contextual_prepend()` | Thêm context "chunk nằm ở đâu" (Anthropic style) |
| Auto Metadata | `extract_metadata()` | LLM extract topic, entities, category |
| Full pipeline | `enrich_chunks()` | Chạy tất cả techniques trên list chunks |

### TODO trong code
```python
# TODO 1: summarize_chunk() — LLM tóm tắt 2-3 câu, hoặc extractive (lấy 2 câu đầu)
# TODO 2: generate_hypothesis_questions() — LLM generate N câu hỏi chunk có thể trả lời
# TODO 3: contextual_prepend() — LLM viết 1 câu context + prepend vào chunk
# TODO 4: extract_metadata() — LLM extract JSON {topic, entities, category, language}
# TODO 5: enrich_chunks() — chạy pipeline trên list chunks, trả về EnrichedChunk
```

### Test pass criteria
- [ ] `summarize_chunk()` trả về string
- [ ] `generate_hypothesis_questions()` trả về list câu hỏi
- [ ] `contextual_prepend()` trả về string chứa original text
- [ ] `extract_metadata()` trả về dict
- [ ] `enrich_chunks()` trả về list `EnrichedChunk` với `original_text` preserved

### Lưu ý
- Cần `OPENAI_API_KEY` trong `.env` (hoặc dùng extractive fallback không cần API)
- Enrichment = **one-time cost** khi indexing. Dùng `gpt-4o-mini` để tiết kiệm
- ROI cao: cải thiện **mọi query** sau đó
