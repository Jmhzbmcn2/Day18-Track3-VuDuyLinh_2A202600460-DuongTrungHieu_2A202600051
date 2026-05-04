# Hệ thống chấm điểm — Lab 18

**Tổng: 100 điểm + 10 bonus**

---

## Phần A: Cá nhân (60 điểm)

| # | Tiêu chí | Điểm | Cách chấm |
|---|----------|------|-----------|
| A1 | Module implementation đúng logic | 15 | Code review: logic đúng, không hardcode |
| A2 | Test pass (`pytest tests/test_m*.py`) | 15 | Auto: số tests pass / tổng tests |
| A3 | Vietnamese-specific handling | 10 | Có dùng underthesea/bge-m3/bge-reranker? |
| A4 | Code quality | 10 | Comments, type hints, `ruff check` pass |
| A5 | TODO markers hoàn thành | 10 | Grep `# TODO` → 0 remaining |

### Auto-grading commands

```bash
# A2: Test pass
pytest tests/test_m1.py -v    # Module 1
pytest tests/test_m2.py -v    # Module 2
pytest tests/test_m3.py -v    # Module 3
pytest tests/test_m4.py -v    # Module 4

# A4: Lint
ruff check src/

# A5: TODO count
grep -r "# TODO" src/m*.py | wc -l    # Should be 0
```

### Thang điểm A2 (test pass)

| Tests pass | Điểm |
|-----------|------|
| 100% | 15 |
| ≥ 80% | 12 |
| ≥ 60% | 9 |
| ≥ 40% | 6 |
| < 40% | 3 |

---

## Phần B: Nhóm (40 điểm)

| # | Tiêu chí | Điểm | Cách chấm |
|---|----------|------|-----------|
| B1 | Pipeline chạy end-to-end | 10 | `python src/pipeline.py` exit code 0 |
| B2 | RAGAS ≥ 0.75 (any metric) | 10 | Check `ragas_report.json` |
| B3 | Failure analysis có insight | 10 | Review `failure_analysis.md` |
| B4 | Presentation rõ ràng | 10 | 4 điểm trình bày đầy đủ |

### Thang điểm B2 (RAGAS)

| Điều kiện | Điểm |
|-----------|------|
| ≥ 2 metrics đạt 0.75 | 10 |
| 1 metric đạt 0.75 | 7 |
| Best metric ≥ 0.60 | 4 |
| Pipeline chạy nhưng scores thấp | 2 |

### Thang điểm B3 (Failure analysis)

| Điều kiện | Điểm |
|-----------|------|
| Bottom-5 có diagnosis + fix + Error Tree walkthrough | 10 |
| Bottom-5 có diagnosis nhưng thiếu Error Tree | 7 |
| Có liệt kê failures nhưng không phân tích | 4 |
| Không có failure analysis | 0 |

### Thang điểm B4 (Presentation)

| Điều kiện | Điểm |
|-----------|------|
| 4/4 điểm trình bày, có số liệu, rõ ràng | 10 |
| 3/4 điểm hoặc thiếu số liệu | 7 |
| 2/4 điểm | 4 |
| Không present | 0 |

---

## Bonus (+10 max)

| Bonus | Điểm | Kiểm tra |
|-------|------|----------|
| RAGAS Faithfulness ≥ 0.85 | +5 | `ragas_report.json` → faithfulness |
| Enrichment pipeline integrated | +3 | Code review: contextual prepend hoặc HyQA |
| Latency breakdown report | +2 | Có bảng thời gian từng bước |

---

## Tổng hợp

```
Điểm cuối = Cá nhân (A1-A5, max 60) + Nhóm (B1-B4, max 40) + Bonus (max 10)
           = max 110 điểm, cap tại 100
```

---

## ⚠️ Điểm liệt

> Nếu nhóm **không có RAGAS evaluation** (M4 không implement) hoặc **không có failure analysis**, điểm tối đa phần Nhóm bị giới hạn ở **20 điểm**.

---

## 📋 Quy trình nộp bài

1. Chạy `python main.py` để tạo reports
2. Điền `analysis/failure_analysis.md` và `analysis/group_report.md`
3. Mỗi người viết `analysis/reflections/reflection_[Tên].md`
4. Chạy `python check_lab.py` để kiểm tra
5. Push lên GitHub, nộp link repo

> Lỗi định dạng khiến `check_lab.py` báo lỗi → **trừ 5 điểm thủ tục**.

---

## 👤 Individual Reflection (bắt buộc)

Mỗi thành viên nộp file `analysis/reflections/reflection_[Tên].md` gồm:
- Đóng góp kỹ thuật cụ thể (module nào, hàm nào)
- Kiến thức học được + kết nối với bài giảng
- Khó khăn & cách giải quyết
- Tự đánh giá 1-5

File reflection được dùng để xác minh đóng góp cá nhân khi chấm điểm A1-A5.
