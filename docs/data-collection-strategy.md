# AI Health Assistant — Chiến lược Thu thập & Chuẩn hóa Dữ liệu (5.000 mẫu)

> Tài liệu này cụ thể hóa quyết định đã thống nhất trước đó (ưu tiên dataset mở + sinh synthetic có grounding), áp dụng đúng vào 7 bảng đã hoàn thiện trong ERD/models (`Patient`, `User`, `ChatSession`, `Message`, `Diagnosis`, `Medication`, `VisitLog`).

---

## 1. Xác định rõ "5.000 mẫu" là gì — cần tách 2 tầng dữ liệu

Đây là điểm quan trọng nhất cần thống nhất trước, vì nó quyết định toàn bộ pipeline phía sau:

| Tầng | Là gì | Số lượng |
|---|---|---|
| **Tầng 1 — Nguyên liệu (content)** | Các cặp Hỏi-Đáp y khoa lấy từ dataset mở (`vietnamese-medical-qa`, ViMQ...) — đây là **nội dung y khoa thô**, chưa có patient_id/session/timeline | **5.000 cặp QA** (chọn lọc từ ~9.335 cặp có sẵn của `vietnamese-medical-qa` + bổ sung ViMQ nếu cần đa dạng chủ đề) |
| **Tầng 2 — Dữ liệu hệ thống (structured)** | Sau khi "diễn giải" Tầng 1 thành hội thoại nhiều lượt + gắn `patient_id`/`session_id`/`timestamp` theo đúng schema DB | **Số lượng lớn hơn 5.000** — vì 1 cặp QA gốc sẽ "nở ra" thành nhiều bản ghi (nhiều `Message`, 1 `Diagnosis`, có thể 1 `Medication`, nhiều `VisitLog`) |

→ **Khuyến nghị**: coi **5.000 là số lượng ở Tầng 1** (nguyên liệu nội dung y khoa đã qua kiểm chứng), còn Tầng 2 (dữ liệu nạp vào hệ thống để test/demo) sẽ có số lượng bản ghi nhiều hơn, tính toán cụ thể ở mục 5.

---

## 2. Nguồn cho Tầng 1 (5.000 mẫu content)

| Nguồn | Số lượng khả dụng | Lấy bao nhiêu | Lý do |
|---|---|---|---|
| `vietnamese-medical-qa` (HuggingFace, Apache 2.0) | 9.335 cặp QA | ~3.500 | Nguồn chính, license rõ ràng, đã qua biên tập từ edoctor/vinmec |
| ViMQ (VinBrain) | có gán nhãn intent + NER sẵn | ~1.000 | Ưu tiên các mẫu có cấu trúc câu hỏi bệnh nhân tự nhiên, giúp Local Agent học cách trích slot |
| ViHealthQA / ViMedAQA | tùy nguồn công bố | ~500 | Bổ sung đa dạng chủ đề (bệnh mãn tính, thuốc) — cần tự kiểm tra license trước khi dùng |

**Tiêu chí lọc khi chọn 5.000 mẫu** (không lấy ngẫu nhiên toàn bộ):
1. Ưu tiên các câu hỏi có **triệu chứng cụ thể, rõ ràng** (loại bỏ câu hỏi quá chung chung như "làm sao để khỏe mạnh?").
2. Đảm bảo **phân bố đa dạng theo chuyên khoa** (nội, nhi, da liễu, tiêu hóa, hô hấp...) — tránh dữ liệu dồn hết vào 1-2 chủ đề phổ biến.
3. Cố tình giữ lại một tỷ lệ nhỏ (~3-5%, tức ~150-250 mẫu) câu hỏi có **dấu hiệu triệu chứng nghiêm trọng** (đau ngực, khó thở, chảy máu nhiều...) — để sau này có dữ liệu **test riêng cho SafetyGate** (kiểm tra Pre-check có chặn đúng không).

---

## 3. Quy trình chuyển đổi 1 cặp QA → dữ liệu hệ thống (Tầng 1 → Tầng 2)

### Ví dụ cụ thể — bắt đầu từ 1 mẫu nguyên liệu thật

**Input (Tầng 1 — từ `vietnamese-medical-qa`):**
```json
{
  "source_id": "vmqa_00214",
  "question": "Tôi bị đau bụng âm ỉ vùng thượng vị 3 ngày nay, kèm ợ chua, ăn không ngon. Tôi bị bệnh gì?",
  "answer": "Triệu chứng của bạn gợi ý viêm dạ dày hoặc trào ngược dạ dày thực quản. Nên hạn chế đồ cay nóng, ăn đúng giờ, nếu không đỡ sau 5-7 ngày cần nội soi dạ dày.",
  "license": "Apache-2.0",
  "source_dataset": "vietnamese-medical-qa"
}
```

### Bước A — Tạo Patient persona (nếu chưa có, hoặc tái sử dụng persona đã tạo)
```json
{
  "patient_id": "a1b2c3d4-...",
  "dob": "1992-03-14",
  "gender": "female",
  "chronic_conditions": [],
  "allergies": []
}
```

### Bước B — Tạo Session (1 lần "khám" tương ứng với 1 cặp QA gốc)
```json
{
  "session_id": "s-0001",
  "patient_id": "a1b2c3d4-...",
  "started_at": "2026-02-10T09:00:00Z",
  "ended_at": "2026-02-10T09:06:00Z",
  "status": "completed"
}
```

### Bước C — Diễn giải câu hỏi gốc thành hội thoại nhiều lượt (dùng LLM, có kiểm soát)

Đây là bước quan trọng nhất — **không copy nguyên câu hỏi/trả lời gốc** (vi phạm bản quyền + không đúng dạng hội thoại thật), mà dùng LLM để **viết lại thành nhiều lượt hỏi-đáp kiểu Symptom Intake**, grounding chặt vào nội dung y khoa gốc:

```json
[
  {
    "message_id": "m-0001",
    "session_id": "s-0001",
    "patient_id": "a1b2c3d4-...",
    "role": "assistant",
    "content": "Chào bạn, bạn đang gặp triệu chứng gì?",
    "extracted_slots": {},
    "created_at": "2026-02-10T09:00:00Z"
  },
  {
    "message_id": "m-0002",
    "session_id": "s-0001",
    "patient_id": "a1b2c3d4-...",
    "role": "user",
    "content": "Em bị đau âm ỉ vùng bụng trên, gần ức, mấy hôm nay rồi.",
    "extracted_slots": {
      "symptoms": ["đau bụng vùng thượng vị"],
      "duration": "3 ngày",
      "severity": "âm ỉ"
    },
    "created_at": "2026-02-10T09:01:00Z"
  },
  {
    "message_id": "m-0003",
    "session_id": "s-0001",
    "patient_id": "a1b2c3d4-...",
    "role": "assistant",
    "content": "Bạn có bị ợ chua hay ăn uống kém đi không?",
    "extracted_slots": {},
    "created_at": "2026-02-10T09:02:00Z"
  },
  {
    "message_id": "m-0004",
    "session_id": "s-0001",
    "patient_id": "a1b2c3d4-...",
    "role": "user",
    "content": "Dạ có, em ợ chua suốt, mà ăn không thấy ngon miệng.",
    "extracted_slots": {
      "symptoms": ["đau bụng vùng thượng vị", "ợ chua", "chán ăn"],
      "duration": "3 ngày"
    },
    "created_at": "2026-02-10T09:03:00Z"
  }
]
```

### Bước D — Sinh `Diagnosis` (grounding vào phần "answer" gốc)
```json
{
  "diagnosis_id": "d-0001",
  "patient_id": "a1b2c3d4-...",
  "session_id": "s-0001",
  "differential_list": [
    { "condition": "Viêm dạ dày", "confidence": 0.62 },
    { "condition": "Trào ngược dạ dày thực quản (GERD)", "confidence": 0.31 }
  ],
  "agent_votes": [
    { "specialist": "noi_tieu_hoa", "opinion": "Nghiêng về viêm dạ dày do đau thượng vị kèm ợ chua" }
  ],
  "triage_level": "see_doctor",
  "created_at": "2026-02-10T09:05:00Z"
}
```

### Bước E — `VisitLog` (snapshot audit trail, liên kết Diagnosis vào timeline)
```json
{
  "log_id": "vl-0001",
  "patient_id": "a1b2c3d4-...",
  "session_id": "s-0001",
  "type": "diagnosis",
  "data": { "diagnosis_id": "d-0001", "triage_level": "see_doctor" },
  "created_at": "2026-02-10T09:05:00Z"
}
```

### Bước F — Metadata truy vết (bắt buộc, gắn kèm mọi bản ghi sinh ra từ Tầng 1)
```json
{
  "generation_metadata": {
    "source_id": "vmqa_00214",
    "source_dataset": "vietnamese-medical-qa",
    "license": "Apache-2.0",
    "generation_method": "llm_grounded_synthetic",
    "reviewed_by_expert": false,
    "generated_at": "2026-02-10T09:10:00Z"
  }
}
```
> Field `generation_metadata` này **không lưu vào bảng production** (`Diagnosis`, `Message`...) — nó chỉ tồn tại ở lớp **dataset trung gian** (Tầng 2 dạng file, trước khi nạp vào DB), dùng để bạn chứng minh nguồn gốc dữ liệu khi viết luận văn. Khi nạp vào DB thật, chỉ giữ lại đúng field của schema production.

---

## 4. Nơi lưu trữ: Dataset (file) hay JSON — câu trả lời là **cả hai, theo đúng lớp (layer)**

Đây là mở rộng của nguyên tắc "raw + processed" đã thống nhất trước, giờ áp dụng cụ thể cho 3 lớp:

```
data/
├── raw/                                  ← KHÔNG sửa, giữ nguyên định dạng gốc
│   ├── vietnamese-medical-qa/
│   │   └── train.parquet                 (tải thẳng từ HuggingFace)
│   └── vimq/
│       └── vimq_raw.csv
│
├── intermediate/                         ← Tầng 1 đã lọc + chuẩn hóa (5.000 mẫu)
│   └── qa_pool.jsonl                     ← mỗi dòng 1 object: {source_id, question, answer, license, source_dataset}
│
├── synthetic/                            ← Tầng 2 — dữ liệu đã "nở ra" thành cấu trúc hệ thống
│   ├── patients.jsonl
│   ├── sessions.jsonl
│   ├── messages.jsonl
│   ├── diagnoses.jsonl
│   ├── medications.jsonl
│   ├── visit_logs.jsonl
│   └── generation_metadata.jsonl         ← truy vết riêng, KHÔNG trộn vào các file trên
│
└── scripts/
    ├── 01_filter_qa_pool.py              ← lọc 5.000 mẫu từ raw theo tiêu chí mục 2
    ├── 02_generate_synthetic.py          ← chạy LLM để sinh hội thoại (Bước C-E ở trên)
    └── 03_load_to_db.py                  ← đọc từ synthetic/*.jsonl, INSERT vào Postgres qua đúng SQLAlchemy models
```

**Vì sao không gộp thẳng thành 1 file JSON lớn duy nhất:**
- **Mỗi file `.jsonl` map đúng 1-1 với 1 bảng trong DB** — giúp bước `03_load_to_db.py` chỉ cần đọc từng file, map thẳng vào đúng model tương ứng (`Patient`, `Message`...), không cần logic tách/phân loại phức tạp.
- **JSONL** (mỗi dòng 1 JSON object) thay vì JSON array lớn — cho phép xử lý theo dòng (streaming), dễ debug (mở 1 dòng lỗi mà không phải load cả file), và dễ append thêm dữ liệu về sau mà không phải parse lại toàn bộ.
- **Tách `generation_metadata.jsonl` riêng** khỏi dữ liệu chính — giữ dữ liệu production sạch, không lẫn field chỉ phục vụ mục đích truy vết/luận văn.

---

## 5. Tính toán khối lượng dữ liệu Tầng 2 (từ 5.000 mẫu Tầng 1)

Để hệ thống thể hiện đúng khả năng "theo dõi diễn biến bệnh" (cần nhiều lần khám/1 bệnh nhân), **không nên** map 1 QA = 1 patient riêng biệt (sẽ tạo ra 5.000 bệnh nhân chỉ khám 1 lần — không test được tính năng theo dõi lâu dài). Thay vào đó:

| Tham số | Giá trị đề xuất | Lý do |
|---|---|---|
| Số lượng **Patient persona** | ~800 - 1.000 | Đủ đa dạng nhân khẩu học (tuổi, giới tính, tiền sử) |
| Số **Session/patient** | 3 - 6 lần khám | Mô phỏng theo dõi bệnh qua thời gian — mỗi lần dùng 1 QA khác nhau nhưng cùng populate 1 nhóm bệnh liên quan (vd 1 bệnh nhân bị viêm dạ dày tái phát 4 lần trong 2 tháng) |
| Tổng **Session** | ~800 × 4 (trung bình) ≈ **3.200 sessions** | |
| **Message/session** | 4 - 8 lượt | |
| Tổng **Message** | ~3.200 × 6 (trung bình) ≈ **~19.000 messages** | |
| Tổng **Diagnosis** | ~1 / session ≈ **3.200** | |
| Tổng **Medication** | ~40-60% session có kê thuốc ≈ **~1.500** | |
| Tổng **VisitLog** | ≥ 1 / session (có thể nhiều nếu 1 session vừa có diagnosis vừa có medication) ≈ **~4.500** | |

→ **5.000 mẫu QA gốc** vẫn đủ làm nguyên liệu, vì mỗi mẫu QA có thể được **tái sử dụng có biến thể** (đổi cách diễn đạt, đổi mức độ nghiêm trọng nhẹ) cho nhiều session khác nhau của cùng 1 nhóm bệnh — không cần 1-1 tuyệt đối giữa QA gốc và session.

**Cách nhóm bệnh để tạo timeline hợp lý**: gom các QA có cùng `differential_list` gần giống nhau (vd cùng liên quan tiêu hóa) thành 1 "cluster bệnh lý", rồi gán ngẫu nhiên có kiểm soát vào các persona phù hợp (tuổi/giới tính hợp lý với bệnh đó).

---

## 6. Rủi ro dữ liệu cần chủ động phòng tránh

| Rủi ro | Cách phòng tránh |
|---|---|
| **Trùng lặp/thiếu đa dạng** (nhiều QA na ná nhau) | Chạy dedup bằng embedding similarity (vd cosine similarity > 0.9 → loại bớt) trước khi đưa vào bước sinh synthetic |
| **Lệch phân bố triage_level** (đa số câu hỏi mở đều nhẹ, thiếu case khẩn cấp để test SafetyGate) | Chủ động giữ tỷ lệ tối thiểu 3-5% case nghiêm trọng như đã nêu ở mục 2, đánh dấu riêng để test |
| **Dữ liệu sinh ra sai lệch y khoa** (LLM tự bịa thêm chi tiết không có trong answer gốc) | Luôn kèm `source_id` để đối chiếu ngược; nên có bước review mẫu (dù chỉ random-sample 5-10%) bởi người có chuyên môn nếu có thể tiếp cận |
| **Thiếu field khi nạp vào DB** (schema Tầng 2 không khớp hoàn toàn với model SQLAlchemy) | Viết `03_load_to_db.py` dùng **chính Pydantic schema đã định nghĩa trong `schemas/`** để validate từng dòng JSONL trước khi insert — dòng nào lỗi validate thì log lại, không chặn cả batch |
| **Session/Message hội thoại nghe "giả", không tự nhiên** | Review thủ công 1 tập nhỏ (~50-100 hội thoại) trước khi chạy sinh hàng loạt, để tinh chỉnh lại prompt sinh dữ liệu (Bước C) nếu văn phong chưa tự nhiên |
| **License không rõ ràng ở 1 số nguồn bổ sung** (ViHealthQA...) | Kiểm tra kỹ trước khi đưa vào `raw/`; nếu không chắc license, chỉ dùng nội bộ cho luận văn, không public lại dataset |

---

## 7. Trình tự thực hiện đề xuất

1. Tải `vietnamese-medical-qa` + ViMQ vào `data/raw/`.
2. Viết `01_filter_qa_pool.py`: lọc + dedup → xuất `intermediate/qa_pool.jsonl` (5.000 dòng).
3. Thiết kế ~800-1.000 patient persona (script random có kiểm soát phân bố tuổi/giới).
4. Nhóm QA theo cluster bệnh lý, gán vào persona để tạo timeline nhiều session/1 bệnh nhân.
5. Viết `02_generate_synthetic.py`: với mỗi (persona, session, QA gốc) → gọi LLM sinh hội thoại (Bước C) + diagnosis (Bước D) + visit_log (Bước E), ghi ra `synthetic/*.jsonl`.
6. Review thủ công 1 tập mẫu nhỏ trước khi chạy full batch.
7. Viết `03_load_to_db.py`: đọc từng file `.jsonl`, validate qua Pydantic schema, insert vào Postgres theo đúng thứ tự (Patient → Session → Message/Diagnosis/Medication → VisitLog, vì có ràng buộc khóa ngoại).