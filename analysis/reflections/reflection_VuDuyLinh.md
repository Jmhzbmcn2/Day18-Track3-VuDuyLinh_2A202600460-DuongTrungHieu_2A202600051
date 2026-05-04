# Individual Reflection — Vũ Duy Linh

**Tên:** Vũ Duy Linh  
**Module phụ trách:** M3 (Reranking) · M4 (RAGAS Evaluation) · M5 (Enrichment Pipeline) · Pipeline Integration

---

## 1. Công việc đã thực hiện

- **Module M3 — Reranking:**
  - Implement `CrossEncoderReranker` (BAAI/bge-reranker-v2-m3, device=cpu) với `benchmark_reranker()` đo latency avg/min/max.
  - Implement `RemoteReranker` — gọi Qwen3-Reranker-0.6B qua Cohere-compatible API (`POST /rerank`) hosted tại `localhost:7997`, batch=16.
  - Số tests pass: 5/5

- **Module M4 — RAGAS Evaluation:**
  - Implement `evaluate_ragas()` với 4 metrics: Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall.
  - Fix critical bug: bypass RAGAS internal executor (gây hang với local LLM) bằng custom sequential `asyncio` loop gọi `_ascore()` trực tiếp.
  - Implement `failure_analysis()` với Diagnostic Tree mapping worst metric → diagnosis → suggested fix.
  - Số tests pass: 4/4

- **Module M5 — Enrichment Pipeline:**
  - Implement `summarize_chunk()`, `generate_hypothesis_questions()`, `contextual_prepend()`, `extract_metadata()`, `enrich_chunks()`.
  - Chuyển toàn bộ từ OpenRouter sang local Qwen2.5-14B-Instruct-AWQ (`localhost:8000/v1`).
  - Số tests pass: 6/6 (kể cả `test_contextual_contains_original`)

- **Pipeline Integration (`src/pipeline.py`):**
  - Ghép M1→M5→M2→M3→M4 thành Production RAG pipeline end-to-end.
  - Thêm latency tracking cho từng bước (chunking/enrichment/indexing/generation/ragas).
  - Cấu hình index **toàn bộ 302 chunks** (thay vì giới hạn 50) để cover đủ 20 câu hỏi test set.

- **Xử lý Dữ liệu (OCR):**
  - Script OCR dùng `pypdf` + `pytesseract` để extract `BCTC.pdf` (PDF scan, không có text layer) → `BCTC.md`.
  - Convert Nghị định 13/2023 từ `.docx` → `13_2023_ND-CP_465185.docx.md` (91KB).

- **Kết quả thực nghiệm (dữ liệu thật, 20 câu hỏi):**

| Metric | Score |
|--------|-------|
| Faithfulness | **0.828** ✅ |
| Answer Relevancy | 0.589 |
| Context Precision | **0.829** ✅ |
| Context Recall | **0.800** ✅ |

## 2. Thử thách lớn nhất & Cách giải quyết

**Thử thách 1 — RAGAS hang hoàn toàn ở 0/80:**  
RAGAS 0.1.21 dùng `asyncio.Semaphore(max_workers=16)` để dispatch 16 LLM calls đồng thời. Local vLLM đang handle Qwen2.5-14B → không đủ capacity → toàn bộ 80 coroutine deadlock chờ nhau.  
**Cách giải quyết:** Debug từng lớp (LLM call → LangchainLLMWrapper → metric.ascore → evaluate executor). Phát hiện `evaluate()` dùng callback manager gây overhead không đoán trước được. Bypass hoàn toàn executor của RAGAS, viết lại vòng lặp `asyncio.run(_run_all())` gọi `metric._ascore()` tuần tự từng câu. Kết quả: chạy được toàn bộ 20 câu × 4 metrics = 80 calls trong 243 giây.

**Thử thách 2 — GPU OOM khi load CrossEncoder:**  
Qwen2.5-14B chiếm ~19 GiB VRAM, không còn chỗ cho CrossEncoder (cần thêm ~16 MiB). PyTorch OOM ngay khi gọi `.to(device)`.  
**Cách giải quyết:** Chuyển CrossEncoder sang `device="cpu"`. Tốc độ chậm hơn nhưng chấp nhận được vì reranker chỉ xử lý 20 docs/query. Đồng thời migrate pipeline sang `RemoteReranker` dùng Qwen3-Reranker-0.6B hosted riêng tại port 7997 — giải pháp production đúng nghĩa.

**Thử thách 3 — BCTC là PDF scan, không có text layer:**  
`pdf2image` / `PyMuPDF` không thể extract text. Phải OCR toàn bộ.  
**Cách giải quyết:** Dùng `pypdf` bóc tách image stream từ PDF → `PIL` + `pytesseract` (tiếng Việt) → Markdown. Bypass hoàn toàn dependency C++ (Poppler).

## 3. Bài học rút ra (Key Learnings)

- **RAGAS + Local LLM cần custom executor:** RAGAS được thiết kế cho cloud API (OpenAI) có thể xử lý concurrent requests. Với local model, phải force sequential và bypass executor mặc định.
- **`is_multiple_completion_supported` là chìa khoá:** RAGAS dùng hàm này để quyết định có pass param `n` vào API hay không. Hiểu được cơ chế này giúp debug nhanh hơn nhiều.
- **Garbage In, Garbage Out — đúng với BCTC:** Q1 "kê khai thuế GTGT kỳ nào?" có context_precision=0 vì bảng số liệu trong PDF scan bị OCR sai format. Pipeline tốt đến đâu cũng không cứu được nếu data ingestion hỏng.
- **Local LLM stack = linh hoạt cao:** Tổ hợp Ollama (embedding) + vLLM Qwen (generation) + vLLM Qwen3-Reranker (reranking) chạy hoàn toàn offline, bảo mật dữ liệu tuyệt đối, chi phí $0/query sau khi setup.

## 4. Đề xuất cải tiến (Next Steps)

1. **HyQA Enrichment cho BCTC tables:** Với các chunk chứa bảng số liệu tài chính, generate câu hỏi giả thiết như "DHA Surfaces nộp thuế GTGT kỳ Q4/2024 bao nhiêu?" → index câu hỏi này → BM25 match exact keyword. Dự kiến fix được bottom-1 failure case (context_precision/recall = 0).
2. **Async embedding để giảm indexing time:** 302 chunks × Ollama embedding = 30.36s. Dùng `asyncio.gather()` gọi Ollama embedding song song (Ollama hỗ trợ concurrent) → ước tính giảm xuống < 10s.
3. **Answer format prompt engineering:** Answer Relevancy = 0.589 phần lớn do LLM trả lời dạng đoạn văn thay vì số liệu ngắn gọn. Thêm instruction "Trả lời ngắn gọn trong 1-2 câu, ưu tiên số liệu cụ thể" vào system prompt → AnswerRelevancy dự kiến tăng lên > 0.75.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5 |
| Code quality | 4 |
| Teamwork | 5 |
| Problem solving | 5 |
