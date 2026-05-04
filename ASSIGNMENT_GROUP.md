# Phần B: Bài tập nhóm — Ghép thành Production RAG System

**Thời gian:** 30 phút · **Điểm:** 40/100 · **Nhóm:** 3–4 người

---

## Mục tiêu

Ghép 4 modules cá nhân thành **1 Production RAG Pipeline** hoàn chỉnh, chạy RAGAS evaluation end-to-end, và so sánh với naive baseline.

---

## Các bước thực hiện

### Bước 1: Integrate (10 phút)

Mở `src/pipeline.py` và ghép modules:

```
M1 (Chunking) → M2 (Hybrid Search) → M3 (Reranking) → LLM Generate → M4 (Evaluation)
```

**Nếu 1 module chưa xong:** mỗi module có fallback implementation (return basic results). Pipeline vẫn chạy được — chỉ scores thấp hơn ở module đó.

```bash
# Test pipeline chạy được
python src/pipeline.py
```

### Bước 2: Add Enrichment — Bonus (5 phút)

Thêm contextual prepend cho 1 subset documents (optional, +3 bonus):

```python
# Trong pipeline.py, trước bước embed:
# Dùng LLM prepend context cho mỗi chunk
# Xem hướng dẫn trong src/pipeline.py → # BONUS: Enrichment
```

### Bước 3: Run RAGAS Evaluation (5 phút)

```bash
python src/pipeline.py
# Output: ragas_report.json + console scores
```

So sánh với naive baseline (đã chạy ở đầu lab):

| Metric | Naive Baseline | Production Pipeline | Δ |
|--------|---------------|--------------------|----|
| Faithfulness | ? | ? | ? |
| Answer Relevancy | ? | ? | ? |
| Context Precision | ? | ? | ? |
| Context Recall | ? | ? | ? |

### Bước 4: Failure Analysis (5 phút)

1. Mở `ragas_report.json` → tìm bottom-5 questions (scores thấp nhất)
2. Cho mỗi question, đi qua **Error Tree**:
   - Output đúng? → Không
   - Context đúng? → Có/Không → Fix G hoặc Fix R/A
   - Query rewrite OK? → Có/Không → Fix R/A hoặc Fix PreRAG
3. Điền vào `templates/failure_analysis.md`

### Bước 5: Presentation (5 phút/nhóm)

Chuẩn bị trình bày 4 điểm:

1. **RAGAS scores:** naive vs production (bảng so sánh)
2. **Biggest win:** module nào cải thiện nhiều nhất? Tại sao?
3. **Case study:** 1 question cụ thể — đi qua Error Tree, chỉ ra root cause
4. **Next step:** nếu có thêm 1 giờ, sẽ optimize gì?

---

## Deliverable

Nhóm submit **GitHub repo** chứa:

```
lab18-production-rag/
├── src/
│   ├── m1_chunking.py          # Cá nhân A đã implement
│   ├── m2_search.py            # Cá nhân B đã implement
│   ├── m3_rerank.py            # Cá nhân C đã implement
│   ├── m4_eval.py              # Cá nhân D đã implement
│   └── pipeline.py             # ★ Nhóm ghép
├── reports/
│   ├── ragas_report.json       # ★ Auto-generated (python main.py)
│   └── naive_baseline_report.json
├── analysis/
│   ├── failure_analysis.md     # ★ Nhóm điền
│   ├── group_report.md         # ★ Nhóm điền
│   └── reflections/
│       ├── reflection_NguyenA.md   # ★ Cá nhân
│       ├── reflection_TranB.md
│       └── ...
└── README.md
```

### Trước khi nộp

```bash
python main.py          # Tạo reports/
python check_lab.py     # Kiểm tra định dạng
```

---

## Chấm điểm nhóm (40 điểm)

| Tiêu chí | Điểm | Chi tiết |
|----------|------|---------|
| Pipeline chạy end-to-end | 10 | `python src/pipeline.py` không lỗi |
| RAGAS ≥ 0.75 (bất kỳ metric nào) | 10 | Ít nhất 1 trong 4 metrics đạt 0.75 |
| Failure analysis có insight | 10 | Bottom-5 có diagnosis + suggested fix hợp lý |
| Presentation rõ ràng | 10 | 4 điểm trình bày đầy đủ, có số liệu |

### Bonus (+10 max)

| Bonus | Điểm | Điều kiện |
|-------|------|-----------|
| RAGAS Faithfulness ≥ 0.85 | +5 | Dùng LLM generation + good prompt |
| Enrichment pipeline | +3 | Contextual prepend hoặc HyQA integrated |
| Latency breakdown | +2 | Report thời gian từng bước (chunk/search/rerank/generate) |

---

## Lưu ý

- **Không cần tất cả modules hoàn hảo.** Pipeline có fallback — chạy được ngay cả khi 1-2 modules dùng basic version.
- **Focus vào failure analysis.** Điểm cao nhất đến từ việc hiểu TẠI SAO pipeline fail, không chỉ từ scores cao.
- **Presentation quan trọng.** 5 phút ngắn — chuẩn bị trước, mỗi người nói 1 phần.
