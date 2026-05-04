# Group Report: Production RAG vs Naive Baseline

## 1. RAGAS Scores Comparison

| Metric | Naive Baseline | Production Pipeline | Δ (Improvement) |
|--------|---------------|--------------------|----|
| Faithfulness | 0.45 | **0.828** ✅ | +0.378 |
| Answer Relevancy | 0.50 | **0.589** | +0.089 |
| Context Precision | 0.35 | **0.829** ✅ | +0.479 |
| Context Recall | 0.40 | **0.800** ✅ | +0.400 |

*(Baseline: naive paragraph chunking + dense-only search, không rerank, không enrichment. Production: kết quả thực từ `reports/ragas_report.json`, 20 câu hỏi, dữ liệu thật BCTC + Nghị định 13/2023)*

## 1b. Latency Breakdown (Production Pipeline)

| Bước | Thời gian |
|------|-----------|
| Chunking (M1 — Hierarchical) | 0.0s |
| Enrichment M5 (first 10 chunks) | 5.35s |
| Indexing BM25 + Dense — 302 chunks (M2) | 30.36s |
| Avg per-query Generation (Qwen2.5-14B) | 0.96s |
| RAGAS Evaluation (20 câu × 4 metrics) | 243.15s |

## 2. Biggest Win (Cải thiện lớn nhất)
**Module có tác động lớn nhất:** M2 (Hybrid Search — BM25 + Dense + RRF) kết hợp với M3 (Qwen3-Reranker-0.6B via API).
**Tại sao?**
- **Context Precision tăng từ 0.35 → 0.829 (+0.479):** Lớn nhất trong 4 metrics. BM25 bắt được các từ khoá số học (mã số thuế, số tiền thuế, điều khoản) mà dense vector hay bỏ sót. RRF hợp nhất 2 ranked lists → loại noise. Reranker Qwen3 lọc thêm 20→3 candidates → precision rất cao.
- **Context Recall tăng từ 0.40 → 0.800 (+0.400):** Hierarchical Chunking giữ nguyên ngữ cảnh, không cắt đứt câu dữ liệu quan trọng (như câu số liệu thuế). Kết hợp BM25 bù cho dense khi query có thuật ngữ kỹ thuật tiếng Việt đặc thù.
- **Điểm yếu còn lại — Answer Relevancy (0.589):** Một số câu LLM sinh câu trả lời đúng nội dung nhưng sai format (trả lời dạng đoạn văn thay vì số liệu ngắn gọn), RAGAS AnswerRelevancy penalize.

## 3. Case Study: Phân tích một câu hỏi cụ thể (Từ Error Tree)
**Câu hỏi:** "Công ty DHA Surfaces kê khai thuế GTGT kỳ nào?" — đây là bottom-1 của pipeline (avg_score=0.10).
- **Scores:** faithfulness=0.40 | answer_relevancy=0.00 | context_precision=0.00 | context_recall=0.00
- **Diagnostic Tree:**
  - Output đúng? → Không (answer_relevancy=0)
  - Context đúng? → Không (context_precision=0, context_recall=0)
  - Query rewrite OK? → Không — câu quá ngắn, thiếu keyword
- **Root Cause:** Dữ liệu BCTC được OCR từ PDF scan, bảng kê khai thuế tồn tại dưới dạng table, không có từ khóa "Quý 4" trực tiếp trong text. Dense embedding không match, BM25 cũng không tìm được vì structure bị mất sau OCR.
- **Suggested Fix:** Thêm post-OCR table parser + HyQA Enrichment tạo câu hỏi giả thiết cho chunk này, ví dụ: "DHA Surfaces nộp thuế GTGT kỳ nào?". (Fix G — Data Ingestion + Fix PreRAG — Enrichment)

## 4. Next Step: Nếu có thêm 1 giờ, nhóm sẽ optimize gì?
1. **Parallel/Async Processing:** Chuyển đổi toàn bộ quá trình API Call (OpenRouter) và Embedding (Ollama) trong pipeline sang `asyncio`. Việc gọi đồng thời sẽ giúp giảm thời gian chạy index từ 3-5 phút xuống dưới 20 giây.
2. **Metadata Filtering trong Qdrant:** Mặc dù M5 đã trích xuất `auto_metadata` (topic, category), nhưng hiện tại `m2_search.py` chưa áp dụng query filter. Nếu thêm 1 tầng pre-filter dựa trên metadata trước khi query vector, sẽ tăng Context Precision lên kịch trần.
