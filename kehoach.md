# 1. BỐI CẢNH HIỆN TẠI

Tôi là sinh viên năm 3 ngành AI tại Đại học FPT TP.HCM.

Tôi đang phát triển một hệ thống Document AI có giao diện người dùng.

Hiện tại hệ thống của tôi đã có:

* RAG pipeline.
* Giao diện người dùng.
* Xử lý DOC.
* Xử lý PDF text.
* Xử lý PDF OCR.
* Sử dụng một số model từ Hugging Face.
* Sử dụng một số model/API từ các công ty bên ngoài.

Tuy nhiên kiến trúc hiện tại đang bị MIX.

Cụ thể:

* RAG logic và OCR logic đang nằm chung.
* Một phần OCR được lấy/trích từ một hệ thống RAG trước đây được xây dựng chuyên cho sách giáo khoa.
* OCR hiện tại có một số logic và preprocessing phục vụ trực tiếp cho use case đó.
* Vì vậy OCR chưa phải là một OCR engine độc lập, generic và reusable.
* RAG cũng chưa được tách thành một RAG engine độc lập.
* Việc mix hai thành phần khiến khó bảo trì, khó debug, khó mở rộng và khó tái sử dụng cho các project khác.

TÔI MUỐN THAY ĐỔI KIẾN TRÚC THEO HƯỚNG MODULAR.

---

# 2. MỤC TIÊU KIẾN TRÚC MỚI

Tôi muốn chuyển từ:

MIXED SYSTEM

```text
RAG
 ├── OCR
 ├── preprocessing
 ├── document parsing
 ├── embedding
 ├── retrieval
 └── LLM
```

thành:

MODULAR SYSTEM

```text
Document Quality Gate
        ↓
OCR Engine
        ↓
RAG Engine
        ↓
Hedgedoc / Application
```

Mỗi thành phần phải có trách nhiệm rõ ràng.

---

# 3. KIẾN TRÚC CUỐI CÙNG

Tôi muốn có 3 core components độc lập:

## Component 1 — OCR Engine

Nhiệm vụ:

> Nhận document/image và chuyển thành text hoặc structured document.

OCR Engine KHÔNG được phụ thuộc vào RAG.

Nó không cần biết:

* vector database nào được dùng
* embedding model nào
* LLM nào
* prompt nào
* chatbot nào

OCR chỉ cần:

```text
Input document
→ preprocessing
→ text detection
→ text recognition
→ layout/document parsing nếu cần
→ structured OCR output
```

---

## Component 2 — AI Document Quality Gate

Nhiệm vụ:

> Kiểm tra chất lượng document trước OCR và quyết định document nên đi qua OCR trực tiếp, cần enhancement hay bị reject.

Quality Gate KHÔNG phải OCR.

Quality Gate cũng KHÔNG phải RAG.

Ví dụ:

```text
Document
↓
Quality Gate
↓
Good
→ OCR trực tiếp

Medium
→ Enhancement
→ OCR

Bad
→ Reject / yêu cầu upload lại
```

Quality Gate có thể phát hiện:

* blur
* low resolution
* shadow
* low contrast
* skew
* perspective distortion
* noise
* occlusion
* các yếu tố khác ảnh hưởng OCR

Mục tiêu quan trọng:

> Không chỉ phát hiện ảnh tốt/xấu mà hướng tới đánh giá "OCR readiness".

---

## Component 3 — RAG Engine

Nhiệm vụ:

> Nhận text/structured document và thực hiện retrieval + generation.

RAG Engine KHÔNG chịu trách nhiệm OCR.

Pipeline:

```text
Document text
↓
Cleaning / normalization nếu cần
↓
Chunking
↓
Embedding
↓
Vector DB / Retrieval
↓
Context
↓
LLM
↓
Answer
```

RAG Engine có thể hỗ trợ:

* DOC
* PDF text
* OCR output
* structured document
* nhiều loại embedding model
* nhiều loại LLM/API

Nhưng RAG không được hard-code logic OCR vào bên trong.

---

# 4. HỆ THỐNG THỨ 4: HEDGEDOC

Hedgedoc là application/integration layer.

Hedgedoc không phải core AI engine.

Hedgedoc chịu trách nhiệm:

* UI
* user interaction
* upload file
* orchestration
* authentication/session nếu có
* gọi Quality Gate API
* gọi OCR API
* gọi RAG API
* hiển thị kết quả

Kiến trúc:

```text
                    HEDGEDOC
                       │
             ┌─────────┼─────────┐
             ↓         ↓         ↓
       Quality API   OCR API   RAG API
             │         │         │
             └─────────┼─────────┘
                       ↓
                  Final Result
```

Không được đưa toàn bộ logic của 3 engine trở lại Hedgedoc.

---

# 5. MỤC TIÊU QUAN TRỌNG NHẤT

TÔI KHÔNG MUỐN AGENT GỘP TẤT CẢ LẠI NGAY.

Tôi muốn phát triển theo thứ tự:

PHASE 1
→ Tách OCR khỏi RAG.

PHASE 2
→ Tách RAG thành một engine riêng.

PHASE 3
→ Xây AI Document Quality Gate thành project độc lập.

PHASE 4
→ Mỗi component chạy độc lập và có test/inference riêng.

PHASE 5
→ Xây API cho từng component.

PHASE 6
→ Hedgedoc gọi các API đó để kết hợp lại.

---

# 6. REPOSITORY STRUCTURE MONG MUỐN

Tôi muốn có tối thiểu 3 repository/project riêng:

```text
document-ocr-engine/
document-quality-gate/
document-rag-engine/
```

Sau đó có:

```text
hedgedoc/
```

để tích hợp.

---

# 7. FOLDER STRUCTURE — OCR ENGINE

Đây là OCR riêng, không phụ thuộc RAG.

```text
document-ocr-engine/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── Dockerfile
│
├── configs/
│   ├── default.yaml
│   └── model_configs/
│
├── data/
│   ├── samples/
│   └── test_documents/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_ocr_experiments.ipynb
│   └── 03_evaluation.ipynb
│
├── src/
│   ├── preprocessing/
│   │   ├── resize.py
│   │   ├── denoise.py
│   │   ├── deskew.py
│   │   └── normalization.py
│   │
│   ├── detection/
│   │   └── text_detection.py
│   │
│   ├── recognition/
│   │   └── text_recognition.py
│   │
│   ├── layout/
│   │   └── layout_analysis.py
│   │
│   ├── postprocessing/
│   │   └── text_cleanup.py
│   │
│   ├── models/
│   │   ├── huggingface_backend.py
│   │   ├── paddle_backend.py
│   │   └── external_api_backend.py
│   │
│   ├── pipeline/
│   │   └── ocr_pipeline.py
│   │
│   └── utils/
│
├── api/
│   └── main.py
│
├── tests/
│   ├── test_preprocessing.py
│   ├── test_detection.py
│   ├── test_recognition.py
│   └── test_pipeline.py
│
└── scripts/
```

## OCR ENGINE DESIGN PRINCIPLE

OCR phải có abstraction/backend layer.

Ví dụ:

```text
OCR Engine
   ↓
OCR Backend Interface
   ├── Hugging Face model
   ├── PaddleOCR
   └── External API
```

Mục đích:

Tôi có thể thay model/provider mà không phải sửa toàn bộ pipeline.

External API chỉ là một provider/backend.

Không coi API bên ngoài là "bản thân OCR Engine".

---

# 8. OCR OUTPUT STANDARD

OCR Engine nên trả về schema chuẩn, ví dụ:

```json
{
  "text": "...",
  "pages": [],
  "blocks": [],
  "words": [],
  "bounding_boxes": [],
  "confidence": 0.0,
  "metadata": {}
}
```

Schema có thể thay đổi sau khi nghiên cứu kỹ.

Quan trọng:

RAG phải nhận OCR output thông qua một interface/schema rõ ràng.

Không được import trực tiếp internal OCR code vào RAG nếu không cần thiết.

---

# 9. FOLDER STRUCTURE — AI DOCUMENT QUALITY GATE

Project riêng:

```text
document-quality-gate/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── Dockerfile
│
├── configs/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── samples/
│
├── notebooks/
│   ├── 01_dataset_exploration.ipynb
│   ├── 02_baseline.ipynb
│   ├── 03_finetuning.ipynb
│   └── 04_error_analysis.ipynb
│
├── src/
│   ├── preprocessing/
│   ├── datasets/
│   ├── models/
│   ├── training/
│   ├── evaluation/
│   ├── inference/
│   ├── decision/
│   └── utils/
│
├── api/
│   └── main.py
│
├── tests/
│
└── scripts/
```

Quality Gate phải có output dạng:

```json
{
  "overall_quality": 4.1,
  "ocr_readiness": "medium",
  "issues": [
    "blur",
    "shadow"
  ],
  "recommendation": "enhance_before_ocr"
}
```

Schema chỉ là ví dụ, chưa phải cố định.

---

# 10. FOLDER STRUCTURE — RAG ENGINE

RAG cũng phải độc lập.

```text
document-rag-engine/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── Dockerfile
│
├── configs/
│   ├── embedding.yaml
│   ├── retrieval.yaml
│   └── llm.yaml
│
├── notebooks/
│   ├── 01_ingestion.ipynb
│   ├── 02_chunking.ipynb
│   ├── 03_retrieval.ipynb
│   └── 04_evaluation.ipynb
│
├── src/
│   ├── ingestion/
│   │   ├── document_loader.py
│   │   └── parser.py
│   │
│   ├── normalization/
│   │   └── text_normalizer.py
│   │
│   ├── chunking/
│   │   └── chunker.py
│   │
│   ├── embeddings/
│   │   └── embedding_provider.py
│   │
│   ├── retrieval/
│   │   ├── vector_store.py
│   │   └── retriever.py
│   │
│   ├── generation/
│   │   └── llm_provider.py
│   │
│   ├── pipeline/
│   │   └── rag_pipeline.py
│   │
│   └── evaluation/
│
├── api/
│   └── main.py
│
├── tests/
│
└── scripts/
```

RAG phải có provider abstraction tương tự OCR.

Ví dụ:

```text
Embedding Provider
├── Hugging Face
└── External API

LLM Provider
├── Provider A API
├── Provider B API
└── Local model
```

Mục tiêu:

Không hard-code một model/API cụ thể.

---

# 11. HEDGEDOC STRUCTURE

Sau này:

```text
hedgedoc/
│
├── frontend/
│
├── backend/
│
├── services/
│   ├── quality_gate_client/
│   ├── ocr_client/
│   └── rag_client/
│
├── workflows/
│   └── document_pipeline.py
│
├── configs/
│
└── README.md
```

Hedgedoc chỉ đóng vai trò orchestrator.

Ví dụ workflow:

```text
Upload
 ↓
Quality Gate API
 ↓
Decision
 ├── Reject
 ├── Enhance → OCR API
 └── Direct → OCR API
                 ↓
             RAG API
                 ↓
               Answer
```

---

# 12. MIGRATION PLAN FROM CURRENT MIXED SYSTEM

Đây là phần rất quan trọng.

Tôi KHÔNG muốn rewrite toàn bộ hệ thống hiện tại trong một lần.

Hãy xem hệ thống hiện tại là:

```text
LEGACY / CURRENT SYSTEM
```

Mục tiêu là tách dần.

## Step 1

Xác định toàn bộ code hiện tại liên quan đến:

* OCR
* PDF parsing
* image preprocessing
* RAG
* embeddings
* retrieval
* LLM
* UI

## Step 2

Phân loại mỗi file/module:

```text
OCR
RAG
Shared utility
UI
Provider/API
Legacy
```

## Step 3

Tách OCR logic thành `document-ocr-engine`.

## Step 4

Chạy OCR standalone bằng CLI/test.

Ví dụ:

```bash
python -m ocr_pipeline input.pdf
```

## Step 5

Tách RAG logic thành `document-rag-engine`.

## Step 6

RAG phải nhận text/structured document từ input chuẩn.

Không được phụ thuộc trực tiếp vào OCR implementation.

## Step 7

Sau khi OCR và RAG độc lập:

* viết tests
* viết README
* viết API
* benchmark từng module

## Step 8

Xây `document-quality-gate`.

## Step 9

Tích hợp Quality Gate → OCR.

## Step 10

Tích hợp OCR → RAG.

## Step 11

Tích hợp cả 3 vào Hedgedoc.

---

# 13. API CONTRACT SAU NÀY

Tôi muốn eventual architecture giống:

## Quality API

```http
POST /quality/assess
```

Input:
document/image

Output:
quality JSON

---

## OCR API

```http
POST /ocr/process
```

Input:
document/image

Output:
standardized OCR JSON

---

## RAG API

```http
POST /rag/query
```

Input:
query + document context/index

Output:
answer + citations/retrieved context nếu hỗ trợ

---

# 14. QUAN HỆ GIỮA 3 COMPONENT

Rất quan trọng:

## Quality Gate

KHÔNG phụ thuộc RAG.

## OCR

KHÔNG phụ thuộc RAG.

## RAG

KHÔNG phụ thuộc implementation cụ thể của OCR.

## Hedgedoc

Có thể phụ thuộc tất cả thông qua API/interface.

Mục tiêu:

```text
Quality Gate ─────┐
                  ↓
OCR ─────────────→ Hedgedoc
                  ↑
RAG ──────────────┘
```

---

# 15. VẤN ĐỀ PREPROCESSING

Tôi đang có một điểm dễ nhầm:

OCR preprocessing và AI Document Quality Gate đều có thể xử lý hình ảnh.

Cần phân biệt:

## OCR preprocessing

Mục đích:

> Sửa ảnh để OCR đọc tốt hơn.

Ví dụ:

* resize
* denoise
* deskew
* threshold
* contrast enhancement

## AI Document Quality Gate

Mục đích:

> Kiểm tra chất lượng + xác định vấn đề + quyết định bước tiếp theo.

Ví dụ:

```text
blur HIGH
shadow MEDIUM
resolution LOW

→ recommendation:
enhance_before_ocr
```

Quality Gate giống "bác sĩ khám".

Preprocessing giống "điều trị ban đầu".

OCR giống "người đọc tài liệu".

RAG giống "người tra cứu thông tin từ nội dung đã đọc".

Không được gộp Quality Gate với preprocessing chỉ vì cả hai đều biến đổi image.

---

# 16. IMPORTANT PROJECT PHILOSOPHY

Tôi muốn chuyển từ:

"một RAG project có OCR bên trong"

sang:

"một modular Document AI ecosystem".

Ba core projects:

```text
1. Document OCR Engine
2. AI Document Quality Gate
3. Document RAG Engine
```

và một integrated application:

```text
4. Hedgedoc
```

---

# 17. LÝ DO KIẾN TRÚC NÀY

Tôi muốn từng component có thể:

* chạy độc lập
* test độc lập
* benchmark độc lập
* deploy độc lập
* thay model độc lập
* thay provider/API độc lập
* tái sử dụng trong project khác

Ví dụ:

OCR Engine có thể dùng cho:

* RAG A
* RAG B
* invoice processing
* document extraction
* enterprise search

Quality Gate có thể dùng cho:

* OCR pipeline
* document upload system
* RAG ingestion
* document processing system

RAG Engine có thể dùng cho:

* educational documents
* enterprise knowledge base
* internal assistant
* other document applications

---

# 18. DEVELOPMENT PRIORITY

Không cần làm tất cả cùng lúc.

Ưu tiên:

### Priority 1

Tách OCR khỏi code RAG hiện tại.

### Priority 2

Tách RAG thành engine độc lập.

### Priority 3

Ổn định interface giữa OCR và RAG.

### Priority 4

Xây AI Document Quality Gate.

### Priority 5

Tích hợp Quality Gate → OCR.

### Priority 6

Đưa các module thành API.

### Priority 7

Xây Hedgedoc integration.

---

# 19. KHÔNG ĐƯỢC LÀM

Không:

* rewrite toàn bộ ngay lập tức
* copy-paste code không hiểu
* hard-code API provider
* hard-code OCR model vào RAG
* hard-code embedding model
* tạo abstraction quá phức tạp khi chưa cần
* xây microservices quá sớm chỉ để "trông chuyên nghiệp"
* cố commercialize trước khi kiểm tra license
* dùng external API mà không có interface/backend abstraction
* làm Quality Gate chỉ như một image filter

---

# 20. AGENT CẦN CHUẨN BỊ CHO TÔI

Hãy trước tiên phân tích codebase hiện tại và tạo:

1. Current Architecture Map.
2. Dependency Map.
3. OCR-related files/modules.
4. RAG-related files/modules.
5. Shared utilities.
6. Legacy code.
7. Migration risks.

Sau đó đề xuất:

### Phase A

OCR extraction.

### Phase B

RAG extraction.

### Phase C

Interface/API design.

### Phase D

Quality Gate.

### Phase E

Hedgedoc integration.

Không tự ý rewrite trước khi mapping architecture hiện tại.

---

# 21. FINAL VISION

Tôi muốn sau một thời gian có architecture:

```text
                 HEDGEDOC
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
  QUALITY GATE     OCR          RAG
        │            │            │
        └────────────┴────────────┘
                     │
              Document AI
                  Platform
```

Trong đó:

**Quality Gate**
= kiểm tra và quyết định chất lượng input.

**OCR**
= đọc document.

**RAG**
= truy xuất và trả lời dựa trên document.

**Hedgedoc**
= ứng dụng kết hợp tất cả.

Đây là hướng phát triển chính của tôi.

Mục tiêu trước mắt không phải commercialize ngay mà là:

* architecture sạch
* modular
* reusable
* testable
* deployable
* có chiều sâu kỹ thuật
* dễ phát triển tiếp
* có thể trở thành nền tảng cho nhiều Document AI projects trong tương lai.
