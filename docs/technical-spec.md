# AI Health Assistant — Technical Spec (API Contract)

> Tài liệu này cụ thể hóa kiến trúc đã chốt ở bước thiết kế thành spec kỹ thuật để bắt đầu code: các luồng request/response, schema dữ liệu, hợp đồng API giữa các thành phần.

---

## 1. Tóm tắt kiến trúc đã chốt

```
Client → API Gateway (JWT) → Auth & Patient ID
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   SERVER (Backend)      │
                        │                         │
   ┌── Đầu vào (Symptom Intake) ──┐               │
   │   + Local Agent (NLU trích   │               │
   │     xuất từ hội thoại +      │               │
   │     lịch sử đã nạp sẵn)      │               │
   └───────────────┬───────────────┘               │
                    ▼                               │
              SafetyGate.check_input()  ← Pre-check │
                    ▼                               │
              ══════ Agent call ══════               │
                    ▼                               │
              [AGENT: Diagnostic Support /           │
               Theo dõi tiến triển bệnh /             │
               Minh bạch & giải thích]                │
                    ▼                               │
              SafetyGate.check_output() ← Post-check │
                    ▼                               │
        ┌───────────┴───────────┐                   │
        ▼                       ▼                   │
   Database                Client (response)         │
   (persist theo            (trực tiếp, KHÔNG quay   │
   patient_id + ts)          lại Đầu vào)             │
        │                                             │
        └──→ Đầu vào (nạp lại làm context phiên sau)  │
```

**Quy tắc bất biến (invariant) của toàn hệ thống:**
1. Mọi request đi vào Agent → bắt buộc qua `SafetyGate.check_input()`.
2. Mọi response từ Agent → bắt buộc qua `SafetyGate.check_output()`.
3. Không có ngoại lệ theo module (Diagnostic, Medication đều tuân thủ như nhau).
4. Sau `check_output()`, response đi thẳng về Client — **không** quay lại "Đầu vào" (tránh vòng lặp).
5. Mọi query vào Database đều kèm `patient_id` (không chỉ timestamp).
6. Đọc dữ liệu thuần (không sinh nội dung AI, vd: xem lại đơn thuốc cũ) → không cần qua SafetyGate, chỉ cần Auth xác thực quyền sở hữu.

---

## 2. Danh sách Endpoint (Client ↔ API Gateway)

| Method | Endpoint | Mô tả | Qua SafetyGate? |
|---|---|---|---|
| POST | `/auth/login` | Đăng nhập, trả JWT | Không |
| POST | `/auth/register` | Đăng ký, tạo `patient_id` | Không |
| POST | `/sessions` | Bắt đầu phiên hội thoại mới (nạp context lịch sử) | Không |
| POST | `/sessions/{session_id}/messages` | Gửi tin nhắn hội thoại (Symptom Intake) | Có |
| GET | `/sessions/{session_id}/diagnosis` | Lấy kết quả chẩn đoán gần nhất của phiên | — (đọc kết quả đã persist) |
| POST | `/medications/suggest` | Yêu cầu gợi ý thuốc | Có |
| GET | `/medications` | Xem đơn thuốc hiện tại/lịch sử | Không (đọc thuần, chỉ qua Auth) |
| GET | `/patients/{patient_id}/history` | Xem lịch sử bệnh án | Không (đọc thuần, chỉ qua Auth) |
| GET | `/sessions/{session_id}/explanation` | Lấy giải thích (XAI) cho 1 kết luận | — (đọc kết quả đã persist) |

---

## 3. Schema dữ liệu chính

### 3.1 `Message` (gửi từ Client, request Symptom Intake)
```json
{
  "session_id": "string",
  "patient_id": "string",
  "content": "string",
  "timestamp": "ISO-8601"
}
```

### 3.2 `AgentRequest` (Server → Agent, sau khi qua Pre-check)
```json
{
  "patient_id": "string",
  "session_id": "string",
  "request_type": "diagnostic | progression_tracking | medication_suggestion | explanation",
  "payload": {
    "current_message": "string",
    "extracted_slots": {
      "symptoms": ["string"],
      "onset": "string",
      "severity": "string",
      "duration": "string"
    },
    "context_history": {
      "recent_diagnoses": [ "..." ],
      "current_medications": [ "..." ],
      "chronic_conditions": [ "..." ]
    }
  },
  "safety_flags": {
    "red_flag_detected": false,
    "triage_hint": "normal | urgent | emergency"
  }
}
```

### 3.3 `AgentResponse` (Agent → Server, trước khi qua Post-check)
```json
{
  "patient_id": "string",
  "session_id": "string",
  "response_type": "diagnostic | progression_tracking | medication_suggestion | explanation",
  "result": {
    "differential_diagnosis": [
      { "condition": "string", "confidence": 0.0, "source_refs": ["kb_doc_id"] }
    ],
    "triage_level": "self_monitor | see_doctor | emergency",
    "explanation": {
      "agent_votes": [ { "specialist": "string", "opinion": "string" } ],
      "consensus_score": 0.0
    },
    "medication_suggestion": {
      "items": [ { "name": "string", "dosage": "string", "note": "string" } ],
      "interaction_warnings": ["string"]
    }
  }
}
```

### 3.4 `SafetyCheckResult` (nội bộ SafetyGate)
```json
{
  "passed": true,
  "check_type": "input | output",
  "flags": ["string"],
  "action": "allow | block | escalate",
  "reason": "string"
}
```

### 3.5 Database record — `VisitLog`
```json
{
  "log_id": "string",
  "patient_id": "string",
  "session_id": "string",
  "timestamp": "ISO-8601",
  "type": "diagnosis | medication | progression",
  "data": { "...": "..." }
}
```
> **Bắt buộc**: mọi query đọc/ghi đều filter theo `(patient_id, timestamp)`, không dùng `timestamp` đơn lẻ.

---

## 4. Đặc tả module `SafetyGate` (Pre-check + Post-check dùng chung)

```python
class SafetyGate:
    RED_FLAG_KEYWORDS = [...]  # đau ngực dữ dội, khó thở nặng, ý định tự hại, ...

    def check_input(self, agent_request: AgentRequest) -> SafetyCheckResult:
        """
        - Quét nội dung message/slots để phát hiện triệu chứng khẩn cấp.
        - Nếu phát hiện: set safety_flags.red_flag_detected = True,
          action = "escalate" → chuyển hướng bệnh nhân đến cảnh báo khẩn cấp,
          KHÔNG cho đi tiếp vào Agent.
        - Ngược lại: action = "allow", cho đi tiếp.
        """

    def check_output(self, agent_response: AgentResponse) -> SafetyCheckResult:
        """
        - Kiểm tra AgentResponse có tự ý đưa kết luận "chắc chắn 100%" không
          (bắt buộc phải có disclaimer + confidence < 1.0).
        - Kiểm tra medication_suggestion có interaction_warnings hợp lệ không.
        - Kiểm tra triage_level có nhất quán với red_flag đã phát hiện ở input không.
        - Nếu bất thường: action = "block" hoặc "escalate".
        - Nếu hợp lệ: action = "allow" → cho đi tiếp đến bước persist + trả Client.
        """
```

> Ghi chú thiết kế: hiện tại triển khai dưới dạng 1 class/middleware dùng chung rule-set. Có thể tách thành 2 service riêng sau này nếu đo được nhu cầu scale độc lập (theo đúng thảo luận YAGIN đã thống nhất).

---

## 5. Sequence chi tiết cho 3 luồng chính

### 5.1 Luồng Symptom Intake → Diagnostic
```
Client → Gateway → Auth → Đầu vào (Local Agent trích xuất slot + nạp context)
      → SafetyGate.check_input()
           ├─ nếu red-flag → trả cảnh báo khẩn cấp ngay, KHÔNG gọi Agent
           └─ nếu bình thường → Agent (Diagnostic Support qua Octochains)
      → SafetyGate.check_output()
           ├─ block/escalate nếu bất thường
           └─ allow →
                ├─→ Database (persist VisitLog, patient_id + timestamp)
                ├─→ Đầu vào (nạp context cho lượt hội thoại kế tiếp trong phiên)
                └─→ Client (response cuối cùng)
```

### 5.2 Luồng Yêu cầu gợi ý thuốc
```
Client → Gateway → Auth → Quản lý thuốc & điều trị
      → SafetyGate.check_input()   [giống mọi request khác — không đi tắt]
      → Agent (medication_suggestion)
      → SafetyGate.check_output()  [đặc biệt kiểm tra interaction_warnings]
           └─ allow →
                ├─→ Database ("Ghi lại đơn thuốc", patient_id + timestamp)
                └─→ Client (response)
```

### 5.3 Luồng đọc lịch sử thuần (không qua Agent)
```
Client → Gateway → Auth (xác thực patient_id sở hữu dữ liệu)
      → Database (query trực tiếp theo patient_id)
      → Client
```
> Không qua SafetyGate vì không có nội dung AI mới được sinh ra — chỉ trả dữ liệu đã lưu.

---

## 6. Việc cần làm tiếp theo (gợi ý thứ tự triển khai)

1. Dựng Auth + Patient ID + Database schema trước (nền tảng, không phụ thuộc AI).
2. Implement `SafetyGate` với rule-set red-flag cơ bản (regex/keyword tiếng Việt) — có thể test độc lập không cần Agent thật.
3. Dựng LangGraph flow cho Symptom Intake (chưa cần Octochains, có thể mock Agent trả response giả để test luồng end-to-end trước).
4. Tích hợp Octochains cho Diagnostic Support (specialist agents + aggregator).
5. Nối luồng Medication + Database persist.
6. Viết test cho 3 sequence ở mục 5, đặc biệt test case red-flag bị chặn đúng ở Pre-check.