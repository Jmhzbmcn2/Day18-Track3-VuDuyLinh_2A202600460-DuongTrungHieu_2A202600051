# Individual Reflection — Dương Trung Hiếu

**Tên:** Dương Trung Hiếu  
**Module phụ trách:** M1 (Advanced Chunking) + M2 (Hybrid Search)

---

## 1. Đóng góp kỹ thuật

- **Module M1 — Advanced Chunking:** Implement 3 chiến lược chunking nâng cao:
  - `chunk_semantic()`: dùng `all-MiniLM-L6-v2` encode từng câu, split khi cosine similarity < threshold — tránh cắt giữa ý.
  - `chunk_hierarchical()`: tạo parent (2048 chars) → split thành children (256 chars), mỗi child mang `parent_id` → retrieve child, return parent.
  - `chunk_structure_aware()`: regex parse markdown headers, tạo chunk = header + content, gán `section` vào metadata.
  - `compare_strategies()`: chạy cả 4 strategies, in bảng so sánh avg/min/max length.
- **Module M2 — Hybrid Search:** Implement full hybrid retrieval stack:
  - `segment_vietnamese()`: tích hợp `underthesea.word_tokenize` để xử lý tiếng Việt trước BM25.
  - `BM25Search`: index bằng `BM25Okapi` trên text đã segment, search trả về top-k với `method="bm25"`.
  - `DenseSearch`: embed bằng Ollama (`embeddinggemma:300m`), lưu vào Qdrant in-memory, search bằng cosine.
  - `reciprocal_rank_fusion()`: merge 2 ranked lists theo công thức `score = Σ 1/(k + rank)`.
- Số tests pass: 9/9 (M1) + 5/5 (M2)

## 2. Kiến thức học được

- **Khái niệm mới nhất:** Reciprocal Rank Fusion — cách đơn giản nhưng cực kỳ hiệu quả để merge 2 hệ thống retrieval hoàn toàn khác nhau (lexical vs semantic) mà không cần train thêm bất cứ gì.
- **Điều bất ngờ nhất:** Hierarchical Chunking cải thiện Context Recall rõ rệt không phải vì nó retrieve nhiều hơn, mà vì nó giữ nguyên ngữ cảnh liên tiếp trong parent — LLM không bao giờ bị "mất giữa câu".
- **Kết nối với bài giảng:** Slide "Chunking Strategies" và "Hybrid Search" — thực tế confirm rằng BM25 rất mạnh cho Vietnamese legal/financial text vì các từ khoá chuyên ngành (mã số thuế, điều khoản, kỳ tính thuế) là exact match, không cần semantic similarity.

## 3. Khó khăn & Cách giải quyết

- **Khó khăn lớn nhất:** `underthesea.word_tokenize` chạy rất chậm trên tập dữ liệu lớn (~302 chunks × 256 chars). Mỗi lần index BM25 mất 2-3 giây.
- **Cách giải quyết:** Cache kết quả tokenize vào dict, tránh gọi lại với cùng text. Ngoài ra giảm corpus xuống còn Vietnamese-only tokens (loại stopwords) để BM25 Okapi hoạt động chính xác hơn.
- **Thời gian debug:** ~45 phút cho DenseSearch — ban đầu dùng Qdrant hosted server (port 6333) nhưng server không running, phải chuyển sang `:memory:` mode.

## 4. Nếu làm lại

- **Sẽ làm khác điều gì:** Implement Vietnamese stopword filtering cho BM25 ngay từ đầu, vì hiện tại BM25 đang bao gồm cả stopwords như "là", "của", "và" vào index — noise không cần thiết.
- **Module nào muốn thử tiếp:** M5 Enrichment — đặc biệt là HyQA (Hypothesis Question Answering). Cách generate câu hỏi giả thiết cho từng chunk để bridge vocabulary gap là kỹ thuật cực kỳ thú vị.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 4 |
| Code quality | 4 |
| Teamwork | 5 |
| Problem solving | 4 |
