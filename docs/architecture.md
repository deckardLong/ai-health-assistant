# AI Health Assistant — Sườn Kiến Trúc Dự Án

> LangGraph (state machine điều phối hội thoại) + Octochains (điều phối multi-agent reasoning song song) — dữ liệu tiếng Việt, có đăng nhập, mỗi bệnh nhân có ID riêng để chẩn đoán & theo dõi bệnh án theo thời gian.

---

## 1. Tổng quan bài toán

Hệ thống là một **trợ lý y tế AI dạng chatbot**, người dùng phải đăng nhập, mỗi người dùng gắn với một **Patient ID** duy nhất. Hệ thống thu thập triệu chứng qua hội thoại, hỗ trợ chẩn đoán sơ bộ, lưu lịch sử bệnh án, theo dõi diễn biến bệnh theo thời gian, quản lý thuốc/điều trị, và luôn giải thích được lý do đưa ra gợi ý (explainability) — vì đây là lĩnh vực có rủi ro cao (health-critical domain).

**Nguyên tắc xuyên suốt:** AI **không thay thế bác sĩ**, chỉ hỗ trợ sàng lọc/gợi ý sơ bộ + luôn có cảnh báo & đường dẫn tới nhân viên y tế thật khi cần (human-in-the-loop, escalation).

---

## 2. Kiến trúc tổng thể

```
User → (đăng nhập, Patient ID) → Client (Web/App)
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │   API Gateway / BE        │
                        │  (Auth, Session, RBAC)    │
                        └───────────┬───────────────┘
                                     ▼
                    ┌───────────────────────────────────┐
                    │      LangGraph Orchestrator         │
                    │  (State Graph theo phiên hội thoại  │
                    │   + theo Patient ID xuyên suốt)     │
                    └───────────────┬─────────────────────┘
        ┌────────────┬──────────────┼──────────────┬───────────────┐
        ▼            ▼              ▼              ▼               ▼
  [Node: Intake] [Node: Diagnostic] [Node: Monitor] [Node: Medication] [Node: Explain]
        │              │
        │        ┌─────▼─────────────────────┐
        │        │   Octochains (song song)    │
        │        │  Specialist Agents (đa góc  │
        │        │  nhìn chuyên khoa) →         │
        │        │  Aggregator (Chief           │
        │        │  Consensus) → kết luận       │
        │        └───────────────────────────────┘
        ▼
  [Patient Data Store: EHR-lite, Conversation Log, Vector KB tiếng Việt]
```

**Vì sao kết hợp LangGraph + Octochains thay vì chỉ dùng một cái:**
- **LangGraph**: quản lý *trạng thái phiên* (session state) theo từng bước hội thoại tuần tự, có điều kiện rẽ nhánh (routing), lưu memory theo `patient_id`, checkpoint/resume hội thoại, tích hợp tool-calling, RAG.
- **Octochains**: dùng ở *bên trong* node cần suy luận đa góc nhìn — ví dụ node "Hỗ trợ chẩn đoán": nhiều "specialist agent" (nội khoa, nhi khoa, dị ứng, tâm lý...) phân tích **song song, độc lập** trên cùng bộ triệu chứng, sau đó một `Aggregator` tổng hợp thành kết luận cuối + mức độ đồng thuận. Đây đúng bản chất Octochains: framework nhẹ, zero-dependency, cho *parallel, isolated, collaborative reasoning* trên các *decomposable task*.

→ LangGraph là "xương sống điều phối luồng", Octochains là "bộ não hội chẩn song song" được gọi ra khi cần độ tin cậy cao (chẩn đoán, đánh giá mức độ khẩn cấp).

---

## 3. Các module chức năng

### 3.0 Auth & Patient Identity (nền tảng, không có trong hình gốc nhưng bắt buộc)
- Đăng nhập/đăng ký, xác thực (OTP/email), phân quyền (bệnh nhân / bác sĩ giám sát / admin).
- Mỗi user → 1 `patient_id` cố định, dùng để truy xuất toàn bộ lịch sử, làm khóa cho LangGraph state (`thread_id = patient_id` hoặc `patient_id + session_id`).
- Consent management: bệnh nhân phải đồng ý (opt-in) cho việc AI xử lý dữ liệu sức khỏe của họ — lưu bản ghi consent có timestamp.

### 3.1 Thu thập & quản lý dữ liệu bệnh nhân
- Hồ sơ nền: tuổi, giới tính, tiền sử bệnh, dị ứng, thuốc đang dùng.
- Chuẩn hóa dữ liệu về schema thống nhất (FHIR-lite hoặc schema tự định nghĩa cho tiếng Việt).

### 3.2 Hội thoại thu thập thông tin (Symptom Intake)
- LangGraph node dạng "slot-filling hội thoại": hỏi tuần tự (triệu chứng chính, thời gian khởi phát, mức độ, yếu tố kèm theo...).
- Có thể dùng structured extraction (LLM → JSON) để đổ vào slot, tránh hỏi lại thông tin đã có.

### 3.3 Hỗ trợ chẩn đoán (Diagnostic Support)
- Gọi Octochains: nhiều specialist agent phân tích độc lập trên triệu chứng đã thu thập + RAG trên kho kiến thức y khoa tiếng Việt (ICD-10, phác đồ điều trị công khai).
- Aggregator tổng hợp: (a) danh sách khả năng chẩn đoán phân biệt (differential diagnosis) kèm % tin cậy, (b) mức độ khẩn cấp (triage level), (c) khuyến nghị hành động (tự theo dõi / khám ngay / cấp cứu).
- **Bắt buộc gắn disclaimer** + escalation nếu phát hiện dấu hiệu nguy hiểm (red-flag symptoms).

### 3.4 Theo dõi diễn biến bệnh
- So sánh dữ liệu theo timeline (mỗi lần trò chuyện = 1 điểm dữ liệu gắn `patient_id` + timestamp).
- Phát hiện xu hướng xấu đi (rule-based hoặc model nhẹ), chủ động hỏi thăm định kỳ.

### 3.5 Quản lý thuốc & điều trị
- Lưu đơn thuốc/phác đồ (do bác sĩ nhập hoặc bệnh nhân khai), nhắc uống thuốc, cảnh báo tương tác thuốc cơ bản, nhắc tái khám.

### 3.6 Minh bạch & giải thích (Explainability)
- Với mỗi kết luận từ node Diagnostic, trả về: nguồn kiến thức đã dùng (citation từ KB), agent nào trong Octochains đưa ra ý kiến gì, mức đồng thuận giữa các agent.
- Đây là điểm rất hợp để làm "selling point" học thuật cho luận văn: đo lường explainability, không chỉ accuracy.

### 3.7 (Đề xuất bổ sung) Các module nên có thêm
| Module | Lý do cần thiết |
|---|---|
| **Cảnh báo khẩn cấp / Red-flag detection** | Bắt buộc về mặt an toàn — phát hiện triệu chứng nguy hiểm (đau ngực, khó thở nặng...) → chuyển hướng ngay đến cấp cứu/hotline, không để AI "tự xử lý". |
| **Human-in-the-loop review** | Bác sĩ giám sát có thể xem/duyệt lại kết luận AI trước khi gửi cho bệnh nhân (ít nhất ở giai đoạn thử nghiệm). |
| **Audit log & Traceability** | Ghi lại mọi quyết định của AI, phục vụ kiểm toán, tuân thủ, và debug. |
| **Đặt lịch/nhắc tái khám** | Kết nối lịch hẹn với cơ sở y tế (có thể mock trong phạm vi luận văn). |
| **Đa kênh nhập liệu** | Cho phép nhập triệu chứng qua text, có thể mở rộng giọng nói sau này. |
| **Feedback loop** | Bệnh nhân/bác sĩ đánh giá độ chính xác gợi ý → dùng để cải thiện KB/prompt theo thời gian. |

---

## 4. Data model rút gọn (gợi ý)

```
User        (user_id, patient_id, email, role, consent_status)
Patient     (patient_id, demographics, allergies, chronic_conditions)
Session     (session_id, patient_id, thread_id, started_at, status)
Message     (message_id, session_id, role, content, extracted_slots, timestamp)
Diagnosis   (diagnosis_id, session_id, patient_id, differential_list, confidence,
             triage_level, agent_votes[], created_at)
Medication  (med_id, patient_id, name, dosage, schedule, prescribed_by)
VisitLog    (log_id, patient_id, session_id, symptoms_snapshot, trend_flag, timestamp)
```

---

## 5. Chiến lược dữ liệu: Crawl hay Synthetic? (phần bạn đang phân vân)

Đây là điểm nhạy cảm nhất của dự án, cần tách rõ **2 loại dữ liệu khác nhau** vì chiến lược cho mỗi loại là khác nhau:

### 5.1 Kiến thức y khoa nền (Knowledge Base cho RAG)
→ **Có thể crawl/thu thập hợp pháp**, vì đây là kiến thức công khai, không phải dữ liệu cá nhân:
- Phác đồ điều trị, hướng dẫn chẩn đoán của Bộ Y tế Việt Nam (các văn bản công khai).
- Tài liệu ICD-10 tiếng Việt.
- Bài viết y khoa từ các nguồn uy tín có cho phép sử dụng (cần kiểm tra điều khoản sử dụng/robots.txt từng trang, tránh crawl trang có bản quyền rõ ràng).
- Đây là nguồn dữ liệu **an toàn nhất** để đầu tư công sức đầu tiên — nó quyết định chất lượng chẩn đoán nhiều hơn là dữ liệu hội thoại.

### 5.2 Dữ liệu hội thoại bệnh nhân — triệu chứng, hỏi-đáp (dùng để train/fine-tune hoặc few-shot)
→ **Không nên crawl dữ liệu bệnh nhân thật**. Lý do:
- Vi phạm pháp lý: Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân (Việt Nam) coi dữ liệu sức khỏe là **dữ liệu cá nhân nhạy cảm**, yêu cầu sự đồng ý rõ ràng, xử lý có điều kiện nghiêm ngặt.
- Dữ liệu bệnh án thật trên mạng gần như không có nguồn hợp pháp để crawl tại Việt Nam (khác Mỹ có MIMIC-III đã de-identify và có quy trình xin phép).

**Khuyến nghị: đi theo hướng hybrid, ưu tiên synthetic có kiểm soát chất lượng:**

1. **Synthetic dialogue generation có grounding**: dùng LLM sinh hội thoại bệnh nhân-bác sĩ **dựa trên** case study/phác đồ đã crawl ở bước 5.1 (để đảm bảo tính y khoa đúng), không sinh ngẫu nhiên vô căn cứ.
2. **Template + biến thể**: xây dựng bộ triệu chứng theo từng bệnh phổ biến (từ tài liệu y khoa công khai) → sinh nhiều biến thể cách diễn đạt tiếng Việt (văn nói, viết tắt, sai chính tả tự nhiên) để mô phỏng người dùng thật.
3. **Expert-in-the-loop annotation**: nếu có thể tiếp cận 1–2 người có chuyên môn y tế (kể cả sinh viên y khoa năm cuối) để review/sửa một tập nhỏ dữ liệu synthetic → tăng độ tin cậy, đây thường là điểm cộng lớn cho luận văn.
4. **Public/open Vietnamese medical QA datasets**: nên rà soát xem có bộ dữ liệu Việt hóa mở nào phù hợp (ví dụ các bộ QA y tế từng công bố trên các hội nghị NLP tiếng Việt) — cần tự kiểm tra license trước khi dùng, vì lĩnh vực này thay đổi liên tục.
5. **Không dùng dữ liệu hội thoại thật của người dùng để train mô hình chung** trừ khi có consent rõ ràng + de-identify hoàn toàn + tách biệt khỏi patient_id gốc — chỉ dùng để cải thiện sản phẩm nội bộ (product analytics), không public.

**Tóm gọn quyết định:** Crawl kiến thức y khoa công khai (an toàn) + Sinh dữ liệu hội thoại synthetic có grounding từ kiến thức đó + review bởi người có chuyên môn nếu có thể. Tránh tuyệt đối việc crawl/thu thập bệnh án, hồ sơ bệnh nhân thật từ bất kỳ nguồn nào không có sự đồng ý & pháp lý rõ ràng.

---

## 6. Bảo mật & tuân thủ (bắt buộc nêu trong luận văn)

- Mã hóa dữ liệu at-rest & in-transit.
- RBAC: bệnh nhân chỉ xem dữ liệu của chính mình; bác sĩ giám sát xem theo phân quyền.
- Audit log mọi truy cập vào dữ liệu nhạy cảm.
- De-identification khi dùng dữ liệu cho mục đích phân tích/cải tiến mô hình.
- Tham chiếu khung pháp lý: Nghị định 13/2023/NĐ-CP (Việt Nam); có thể tham khảo thêm nguyên tắc từ HIPAA (Mỹ) như khung tham chiếu học thuật, không bắt buộc tuân thủ trực tiếp.
- Disclaimer rõ ràng ở mọi kết luận chẩn đoán: "Đây là gợi ý tham khảo, không thay thế chẩn đoán của bác sĩ."

---

## 7. Đánh giá hệ thống (Evaluation)

| Thành phần | Metric gợi ý |
|---|---|
| Symptom Intake | Slot-filling accuracy, số lượt hỏi trung bình để đủ thông tin |
| Diagnostic Support | Top-k accuracy so với ground-truth case (từ dữ liệu synthetic có nhãn), calibration của confidence score |
| Octochains consensus | Mức đồng thuận giữa specialist agents, tỉ lệ Aggregator override đúng |
| Explainability | Human eval: bác sĩ/expert đánh giá tính hợp lý của giải thích |
| An toàn | Recall của red-flag detection (ưu tiên recall cao hơn precision) |
| Theo dõi diễn biến | Độ chính xác phát hiện xu hướng xấu đi theo timeline |

---

## 8. Roadmap đề xuất (cho luận văn/capstone)

1. **Giai đoạn 1 — Nền tảng**: Auth + Patient ID, schema dữ liệu, thu thập KB y khoa tiếng Việt (crawl nguồn công khai), xây RAG cơ bản.
2. **Giai đoạn 2 — Core Agent**: LangGraph flow cho Symptom Intake + node Diagnostic gọi Octochains (2–3 specialist agent + 1 aggregator), sinh dữ liệu synthetic có grounding để test.
3. **Giai đoạn 3 — Mở rộng**: Theo dõi diễn biến bệnh, quản lý thuốc, red-flag detection, explainability layer.
4. **Giai đoạn 4 — Đánh giá & viết luận văn**: Human eval với expert (nếu có thể), đo các metric ở mục 7, phân tích hạn chế.

---

## 9. Rủi ro & giới hạn cần nêu rõ trong luận văn

- Dữ liệu synthetic không phản ánh hoàn toàn độ đa dạng của bệnh nhân thật → cần nêu rõ giới hạn generalization.
- Rủi ro AI đưa gợi ý sai trong lĩnh vực sức khỏe → cần chính sách escalation & disclaimer chặt.
- Octochains là framework khá mới/nhẹ, chưa có track record production lớn → nên tự benchmark/so sánh với việc tự cài multi-agent bằng LangGraph thuần để có cơ sở so sánh học thuật.
- Thiếu dữ liệu tiếng Việt chuyên ngành y tế là hạn chế chung của lĩnh vực — nên nêu đây là một phần đóng góp của đề tài (xây dựng pipeline sinh dữ liệu, không chỉ xây model).