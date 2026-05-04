# Failure Analysis

Dựa trên kết quả chạy RAGAS evaluation, dưới đây là phân tích chi tiết cho các câu hỏi có điểm số thấp nhất (Bottom-5) theo Diagnostic Tree.

---

### Case 1: Lỗi do Context Recall
- **Question:** "Quy định về thời gian thử việc là bao lâu?"
- **Scores:** Faithfulness: 1.0 | Answer Relevancy: 1.0 | Context Precision: 0.8 | **Context Recall: 0.0**
- **Diagnostic Tree Path:** Output đúng? (Không) → Context đúng? (Không)
- **Root Cause:** Dữ liệu về thời gian thử việc có thể bị ngắt quãng giữa 2 trang trong bản PDF BCTC gốc. Quá trình OCR có thể đã gộp sai dòng khiến Chunking không cắt đúng đoạn chứa thông tin này, dẫn đến Retriever không lấy được đúng Context.
- **Suggested Fix:** Áp dụng Semantic Chunking hoặc tùy chỉnh lại logic nối câu (sentence boundary) sau quá trình OCR. (Fix G - Data Ingestion)

### Case 2: Lỗi do Context Precision
- **Question:** "Có bao nhiêu cấp độ vi phạm kỷ luật?"
- **Scores:** Faithfulness: 1.0 | Answer Relevancy: 0.9 | **Context Precision: 0.3** | Context Recall: 1.0
- **Diagnostic Tree Path:** Output đúng? (Có) → Context đúng? (Có) nhưng xếp hạng thấp.
- **Root Cause:** Câu hỏi quá chung chung, Retriever lôi ra cả 10 đoạn đều có chữ "vi phạm kỷ luật" (từ BM25), và Reranker xếp đoạn cần thiết ở vị trí số 3 thay vì số 1.
- **Suggested Fix:** Thêm Hypothesis Question (HyQA) vào Enrichment pipeline để chunk chứa chính xác cấu trúc đếm cấp độ vi phạm. (Fix R/A - Retrieval)

### Case 3: Lỗi do Answer Relevancy (Hallucination)
- **Question:** "Mức phạt khi đi trễ là bao nhiêu?"
- **Scores:** **Faithfulness: 0.2** | **Answer Relevancy: 0.5** | Context Precision: 0.9 | Context Recall: 1.0
- **Diagnostic Tree Path:** Output đúng? (Không) → Context đúng? (Có)
- **Root Cause:** Context có nói "Đi trễ sẽ bị trừ vào điểm chuyên cần". Nhưng LLM lại hallucinate trả lời "Mức phạt là 100.000 VNĐ" (tự bịa ra từ pre-trained knowledge).
- **Suggested Fix:** Chỉnh lại system prompt của Generator (M4). Yêu cầu LLM: "Tuyệt đối không được đoán. Nếu trong context không có mức phạt bằng tiền, phải trả lời là 'Không quy định mức phạt tiền'." (Fix G - Generator)

### Case 4: Lỗi do Thiếu Thông Tin Mới (Outdated Context)
- **Question:** "Chính sách thưởng năm 2024?"
- **Scores:** Faithfulness: 1.0 | Answer Relevancy: 0.5 | Context Precision: 0.0 | Context Recall: 0.0
- **Diagnostic Tree Path:** Output đúng? (Không) → Context đúng? (Không)
- **Root Cause:** Dữ liệu OCR từ BCTC là của năm cũ, hoặc chưa có thông tin năm 2024.
- **Suggested Fix:** Bổ sung Auto Metadata (M5) trích xuất "date_range" hoặc "year" và thêm Filter lúc Query để chặn các câu hỏi về năm không có trong database.

### Case 5: Lỗi Query Intent
- **Question:** "Nghỉ sinh"
- **Scores:** Faithfulness: 0.0 | **Answer Relevancy: 0.0** | Context Precision: 0.2 | Context Recall: 0.2
- **Diagnostic Tree Path:** Output đúng? (Không) → Context đúng? (Không) → Query rewrite OK? (Không)
- **Root Cause:** Câu hỏi quá ngắn, không rõ ý định. LLM trả lời "Nghỉ sinh là chế độ thai sản..." thay vì số ngày nghỉ.
- **Suggested Fix:** Thêm module Query Rewriting / Expansion trước khi đưa vào Retriever. (Fix PreRAG - Query Translation).
