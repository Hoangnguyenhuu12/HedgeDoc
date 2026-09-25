"Tôi muốn xây dựng tính năng [Tên tính năng] cho bài toán [Mô tả bài toán].
Ràng buộc của tôi gồm:
- Hạ tầng: [On-premise / Cloud / Có GPU hay không]
- Điều tôi cấm tuyệt đối: [Cấm lộ dữ liệu / Cấm đoán mò / Cấm trễ...]
- Mục tiêu nghiệm thu: [Con số cụ thể]
Hãy dựa vào cấu trúc của 

template-spec-readme.md
, đóng vai trò Kiến trúc sư trưởng và soạn thảo chi tiết bản nháp README.md cho tôi."

flowchart LR
    A["1. Nỗi đau thực tế<br/>(Pain Point)"] 
    A --> B["2. Ràng buộc Hạ tầng<br/>(Hardware / Cost)"]
    B --> C["3. Điều cấm kỵ<br/>(Non-negotiables)"]
    C --> D["4. Đánh đổi<br/>(Trade-offs)"]
    D --> E["5. Nghiệm thu bằng gì?<br/>(Metrics / SLA)"]

Nỗi đau thực tế (Vấn đề nghiệp vụ): Người dùng/doanh nghiệp đang gặp lỗi gì? Mất bao nhiêu tiền/thời gian cho nó? (Ví dụ: Đọc hợp đồng mất 3 tiếng; hoặc phát hiện lỗi bo mạch bằng mắt thường bị sót 5%).
Ràng buộc hạ tầng & Môi trường: Bạn có bao nhiêu tiền/phần cứng? Chạy Cloud (OpenAI, AWS) hay bắt buộc On-Premise nội bộ? Có card GPU không hay chỉ có CPU?
Những điều cấm kỵ (Non-negotiables): Sai sót nào sẽ khiến dự án bị kiện, bị sa thải, mất uy tín hoặc phá sản? (Ví dụ: Cấm rò rỉ dữ liệu mật; cấm AI đoán mò; cấm độ trễ vượt quá 30ms; cấm tự ý đăng bài).
Sẵn sàng đánh đổi cái gì?: Bạn chọn cái gì và chấp nhận hy sinh cái gì? (Ví dụ: Chấp nhận AI phản hồi chậm hơn 5 giây để lấy độ chính xác 100%; hay chấp nhận hy sinh 1% độ chính xác để mô hình chạy được trên chip giá rẻ?).
Nghiệm thu bằng con số nào?: Dự án thế nào là thành công? (Ví dụ: Độ chính xác > 98%, thời gian phản hồi < 2 giây, tỷ lệ ảo giác = 0).