"""
Script to generate rich sample datasets for HedgeDoc:
1. data/raw_docs/bao_cao_kinh_doanh_2025.xlsx (Multi-sheet Excel workbook with comprehensive business data)
2. data/raw_docs/chinh_sach_nhan_su_va_van_hanh_2025.docx (Multi-section Word document with corporate policies)
"""

from pathlib import Path
import pandas as pd
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

RAW_DOCS_DIR = Path(__file__).resolve().parent / "raw_docs"
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)


def generate_excel_data():
    excel_path = RAW_DOCS_DIR / "bao_cao_kinh_doanh_2025.xlsx"
    print(f"Creating Excel workbook: {excel_path}...")

    # 1. Sheet: Tong_Quan (16 rows)
    data_tong_quan = [
        {"Nam": 2025, "Quy": "Q1", "Dong_San_Pham": "Phan_Mem_SaaS", "Doanh_Thu_Ty_VND": 45.2, "Chi_Phi_Ty_VND": 28.5, "Loi_Nhuan_Truoc_Thue_Ty_VND": 16.7, "Ty_Suat_Loi_Nhuan_Percent": 36.9, "Tang_Truong_YoY_Percent": 24.5},
        {"Nam": 2025, "Quy": "Q1", "Dong_San_Pham": "Tu_Van_AI", "Doanh_Thu_Ty_VND": 32.8, "Chi_Phi_Ty_VND": 19.4, "Loi_Nhuan_Truoc_Thue_Ty_VND": 13.4, "Ty_Suat_Loi_Nhuan_Percent": 40.8, "Tang_Truong_YoY_Percent": 68.2},
        {"Nam": 2025, "Quy": "Q1", "Dong_San_Pham": "Thiet_Bi_IoT", "Doanh_Thu_Ty_VND": 18.5, "Chi_Phi_Ty_VND": 14.2, "Loi_Nhuan_Truoc_Thue_Ty_VND": 4.3, "Ty_Suat_Loi_Nhuan_Percent": 23.2, "Tang_Truong_YoY_Percent": 12.1},
        {"Nam": 2025, "Quy": "Q1", "Dong_San_Pham": "Ban_Quyen_Giai_Phap", "Doanh_Thu_Ty_VND": 25.0, "Chi_Phi_Ty_VND": 11.0, "Loi_Nhuan_Truoc_Thue_Ty_VND": 14.0, "Ty_Suat_Loi_Nhuan_Percent": 56.0, "Tang_Truong_YoY_Percent": 18.4},

        {"Nam": 2025, "Quy": "Q2", "Dong_San_Pham": "Phan_Mem_SaaS", "Doanh_Thu_Ty_VND": 52.6, "Chi_Phi_Ty_VND": 31.2, "Loi_Nhuan_Truoc_Thue_Ty_VND": 21.4, "Ty_Suat_Loi_Nhuan_Percent": 40.7, "Tang_Truong_YoY_Percent": 28.3},
        {"Nam": 2025, "Quy": "Q2", "Dong_San_Pham": "Tu_Van_AI", "Doanh_Thu_Ty_VND": 41.5, "Chi_Phi_Ty_VND": 23.1, "Loi_Nhuan_Truoc_Thue_Ty_VND": 18.4, "Ty_Suat_Loi_Nhuan_Percent": 44.3, "Tang_Truong_YoY_Percent": 75.0},
        {"Nam": 2025, "Quy": "Q2", "Dong_San_Pham": "Thiet_Bi_IoT", "Doanh_Thu_Ty_VND": 21.3, "Chi_Phi_Ty_VND": 15.8, "Loi_Nhuan_Truoc_Thue_Ty_VND": 5.5, "Ty_Suat_Loi_Nhuan_Percent": 25.8, "Tang_Truong_YoY_Percent": 15.6},
        {"Nam": 2025, "Quy": "Q2", "Dong_San_Pham": "Ban_Quyen_Giai_Phap", "Doanh_Thu_Ty_VND": 28.4, "Chi_Phi_Ty_VND": 12.5, "Loi_Nhuan_Truoc_Thue_Ty_VND": 15.9, "Ty_Suat_Loi_Nhuan_Percent": 55.9, "Tang_Truong_YoY_Percent": 21.0},

        {"Nam": 2025, "Quy": "Q3", "Dong_San_Pham": "Phan_Mem_SaaS", "Doanh_Thu_Ty_VND": 61.8, "Chi_Phi_Ty_VND": 34.0, "Loi_Nhuan_Truoc_Thue_Ty_VND": 27.8, "Ty_Suat_Loi_Nhuan_Percent": 45.0, "Tang_Truong_YoY_Percent": 33.7},
        {"Nam": 2025, "Quy": "Q3", "Dong_San_Pham": "Tu_Van_AI", "Doanh_Thu_Ty_VND": 56.2, "Chi_Phi_Ty_VND": 29.8, "Loi_Nhuan_Truoc_Thue_Ty_VND": 26.4, "Ty_Suat_Loi_Nhuan_Percent": 47.0, "Tang_Truong_YoY_Percent": 88.5},
        {"Nam": 2025, "Quy": "Q3", "Dong_San_Pham": "Thiet_Bi_IoT", "Doanh_Thu_Ty_VND": 24.6, "Chi_Phi_Ty_VND": 17.5, "Loi_Nhuan_Truoc_Thue_Ty_VND": 7.1, "Ty_Suat_Loi_Nhuan_Percent": 28.8, "Tang_Truong_YoY_Percent": 19.2},
        {"Nam": 2025, "Quy": "Q3", "Dong_San_Pham": "Ban_Quyen_Giai_Phap", "Doanh_Thu_Ty_VND": 31.5, "Chi_Phi_Ty_VND": 13.8, "Loi_Nhuan_Truoc_Thue_Ty_VND": 17.7, "Ty_Suat_Loi_Nhuan_Percent": 56.2, "Tang_Truong_YoY_Percent": 25.1},

        {"Nam": 2025, "Quy": "Q4", "Dong_San_Pham": "Phan_Mem_SaaS", "Doanh_Thu_Ty_VND": 74.5, "Chi_Phi_Ty_VND": 39.2, "Loi_Nhuan_Truoc_Thue_Ty_VND": 35.3, "Ty_Suat_Loi_Nhuan_Percent": 47.4, "Tang_Truong_YoY_Percent": 38.2},
        {"Nam": 2025, "Quy": "Q4", "Dong_San_Pham": "Tu_Van_AI", "Doanh_Thu_Ty_VND": 68.9, "Chi_Phi_Ty_VND": 35.1, "Loi_Nhuan_Truoc_Thue_Ty_VND": 33.8, "Ty_Suat_Loi_Nhuan_Percent": 49.0, "Tang_Truong_YoY_Percent": 94.2},
        {"Nam": 2025, "Quy": "Q4", "Dong_San_Pham": "Thiet_Bi_IoT", "Doanh_Thu_Ty_VND": 30.2, "Chi_Phi_Ty_VND": 21.0, "Loi_Nhuan_Truoc_Thue_Ty_VND": 9.2, "Ty_Suat_Loi_Nhuan_Percent": 30.5, "Tang_Truong_YoY_Percent": 26.4},
        {"Nam": 2025, "Quy": "Q4", "Dong_San_Pham": "Ban_Quyen_Giai_Phap", "Doanh_Thu_Ty_VND": 38.0, "Chi_Phi_Ty_VND": 15.6, "Loi_Nhuan_Truoc_Thue_Ty_VND": 22.4, "Ty_Suat_Loi_Nhuan_Percent": 58.9, "Tang_Truong_YoY_Percent": 30.5},
    ]

    # 2. Sheet: Thi_Truong_Kenh_Ban (24 rows)
    regions = ["Mien_Bac", "Mien_Trung", "Mien_Nam", "Dong_Nam_A"]
    channels = ["B2B_Truc_Tiep", "Dai_Ly_Doi_Tac", "Kenh_Truc_Tuyen"]
    data_thi_truong = []
    base_clients = {"Mien_Bac": 180, "Mien_Trung": 75, "Mien_Nam": 240, "Dong_Nam_A": 45}
    base_rev = {"Mien_Bac": 42.0, "Mien_Trung": 16.5, "Mien_Nam": 58.0, "Dong_Nam_A": 22.0}

    for period in ["6_Thang_Dau_Nam", "6_Thang_Cuoi_Nam"]:
        p_factor = 1.0 if period == "6_Thang_Dau_Nam" else 1.25
        for r in regions:
            for c in channels:
                c_factor = 0.55 if c == "B2B_Truc_Tiep" else (0.30 if c == "Dai_Ly_Doi_Tac" else 0.15)
                clients = int(base_clients[r] * c_factor * (1.1 if period == "6_Thang_Cuoi_Nam" else 1.0))
                rev = round(base_rev[r] * c_factor * p_factor, 2)
                avg_order = round((rev * 1000) / max(1, clients), 1)
                retention = 94.5 if r == "Mien_Nam" else (92.0 if r == "Mien_Bac" else (88.5 if r == "Mien_Trung" else 85.0))
                data_thi_truong.append({
                    "Ky_Bao_Cao": period,
                    "Khu_Vuc": r,
                    "Kenh_Phan_Phoi": c,
                    "So_Luong_Khach_Hang": clients,
                    "Doanh_Thu_Kenh_Ty_VND": rev,
                    "Gia_Tri_Don_TB_Trieu_VND": avg_order,
                    "Ty_Le_Giu_Chan_Percent": retention
                })

    # 3. Sheet: Chi_Phi_Van_Hanh (18 rows)
    data_chi_phi = [
        {"Danh_Muc": "Ha_Tang_Cloud_GCP", "Phong_Ban": "Ky_Thuat_Cloud", "Ngan_Sach_Ke_Hoach_Ty": 18.0, "Thuc_Chi_Ty": 16.8, "Chenh_Lech_Ty": -1.2, "Ty_Le_Giai_Ngan_Percent": 93.3, "Ghi_Chu": "Toi uu hoa BigQuery va Kubernetes"},
        {"Danh_Muc": "Ha_Tang_Cloud_AWS", "Phong_Ban": "Ky_Thuat_Cloud", "Ngan_Sach_Ke_Hoach_Ty": 12.0, "Thuc_Chi_Ty": 12.4, "Chenh_Lech_Ty": 0.4, "Ty_Le_Giai_Ngan_Percent": 103.3, "Ghi_Chu": "Vuot nhe do mo rong cu cum Singapore"},
        {"Danh_Muc": "Nghien_Cuu_Phat_Trien_AI", "Phong_Ban": "Vien_Nghien_Cuu_AI", "Ngan_Sach_Ke_Hoach_Ty": 25.0, "Thuc_Chi_Ty": 24.2, "Chenh_Lech_Ty": -0.8, "Ty_Le_Giai_Ngan_Percent": 96.8, "Ghi_Chu": "Huan luyen mo hinh LLM chuyen nganh"},
        {"Danh_Muc": "Luong_Thuong_Co_Dinh", "Phong_Ban": "Toan_Cong_Ty", "Ngan_Sach_Ke_Hoach_Ty": 65.0, "Thuc_Chi_Ty": 64.1, "Chenh_Lech_Ty": -0.9, "Ty_Le_Giai_Ngan_Percent": 98.6, "Ghi_Chu": "Chi tra day du 12 thang luong"},
        {"Danh_Muc": "Thuong_Hieu_Suat_Du_An", "Phong_Ban": "Khoi_Kinh_Doanh_Tech", "Ngan_Sach_Ke_Hoach_Ty": 18.0, "Thuc_Chi_Ty": 19.5, "Chenh_Lech_Ty": 1.5, "Ty_Le_Giai_Ngan_Percent": 108.3, "Ghi_Chu": "Vuot ke hoach do doanh so Q4 vuot 15%"},
        {"Danh_Muc": "Bao_Hiem_Suc_Khoe_PVI", "Phong_Ban": "Hanh_Chinh_Nhan_Su", "Ngan_Sach_Ke_Hoach_Ty": 3.5, "Thuc_Chi_Ty": 3.2, "Chenh_Lech_Ty": -0.3, "Ty_Le_Giai_Ngan_Percent": 91.4, "Ghi_Chu": "Goi cao cap 150 trieu/nguoi"},
        {"Danh_Muc": "Dao_Tao_Chung_Chi_Quoc_Te", "Phong_Ban": "Hanh_Chinh_Nhan_Su", "Ngan_Sach_Ke_Hoach_Ty": 4.0, "Thuc_Chi_Ty": 3.6, "Chenh_Lech_Ty": -0.4, "Ty_Le_Giai_Ngan_Percent": 90.0, "Ghi_Chu": "45 nhan su dat chung chi GCP/AWS/PMP"},
        {"Danh_Muc": "Marketing_Va_Truyen_Thong", "Phong_Ban": "Khoi_Marketing", "Ngan_Sach_Ke_Hoach_Ty": 16.0, "Thuc_Chi_Ty": 15.1, "Chenh_Lech_Ty": -0.9, "Ty_Le_Giai_Ngan_Percent": 94.4, "Ghi_Chu": "Chien dich TechSummit 2025"},
        {"Danh_Muc": "Thue_Van_Phong_HN_HCM", "Phong_Ban": "Hanh_Chinh_Tong_Hop", "Ngan_Sach_Ke_Hoach_Ty": 8.4, "Thuc_Chi_Ty": 8.4, "Chenh_Lech_Ty": 0.0, "Ty_Le_Giai_Ngan_Percent": 100.0, "Ghi_Chu": "Toa nha Keangnam HN va Bitexco HCM"},
        {"Danh_Muc": "Phap_Ly_Va_Ban_Quyen_Kiem_Toan", "Phong_Ban": "Ban_Kiem_Soat", "Ngan_Sach_Ke_Hoach_Ty": 2.8, "Thuc_Chi_Ty": 2.5, "Chenh_Lech_Ty": -0.3, "Ty_Le_Giai_Ngan_Percent": 89.3, "Ghi_Chu": "Kiem toan Big4 Ernst & Young"},
    ]

    # 4. Sheet: KPI_Nhan_Su (10 departments)
    data_kpi = [
        {"Phong_Ban": "Vien_Nghien_Cuu_AI", "Nhan_Su_Dau_Nam": 35, "Nhan_Su_Cuoi_Nam": 52, "Ty_Le_Bien_Dong_Percent": 4.2, "Diem_KPI_TB": 4.85, "Chi_Tieu_Tuyen_Dung_2026": 20},
        {"Phong_Ban": "Ky_Thuat_Phan_Mem_SaaS", "Nhan_Su_Dau_Nam": 60, "Nhan_Su_Cuoi_Nam": 85, "Ty_Le_Bien_Dong_Percent": 6.8, "Diem_KPI_TB": 4.65, "Chi_Tieu_Tuyen_Dung_2026": 25},
        {"Phong_Ban": "Phan_Cung_IoT", "Nhan_Su_Dau_Nam": 28, "Nhan_Su_Cuoi_Nam": 34, "Ty_Le_Bien_Dong_Percent": 5.5, "Diem_KPI_TB": 4.40, "Chi_Tieu_Tuyen_Dung_2026": 10},
        {"Phong_Ban": "Khoi_Kinh_Doanh_B2B", "Nhan_Su_Dau_Nam": 40, "Nhan_Su_Cuoi_Nam": 58, "Ty_Le_Bien_Dong_Percent": 9.2, "Diem_KPI_TB": 4.75, "Chi_Tieu_Tuyen_Dung_2026": 15},
        {"Phong_Ban": "Tu_Van_Chuyen_Doi_So", "Nhan_Su_Dau_Nam": 22, "Nhan_Su_Cuoi_Nam": 36, "Ty_Le_Bien_Dong_Percent": 3.8, "Diem_KPI_TB": 4.90, "Chi_Tieu_Tuyen_Dung_2026": 12},
        {"Phong_Ban": "Khoi_Marketing_Tang_Truong", "Nhan_Su_Dau_Nam": 18, "Nhan_Su_Cuoi_Nam": 24, "Ty_Le_Bien_Dong_Percent": 8.0, "Diem_KPI_TB": 4.50, "Chi_Tieu_Tuyen_Dung_2026": 8},
        {"Phong_Ban": "Hanh_Chinh_Nhan_Su", "Nhan_Su_Dau_Nam": 12, "Nhan_Su_Cuoi_Nam": 15, "Ty_Le_Bien_Dong_Percent": 2.5, "Diem_KPI_TB": 4.70, "Chi_Tieu_Tuyen_Dung_2026": 4},
        {"Phong_Ban": "Tai_Chinh_Ke_Toan", "Nhan_Su_Dau_Nam": 10, "Nhan_Su_Cuoi_Nam": 12, "Ty_Le_Bien_Dong_Percent": 1.8, "Diem_KPI_TB": 4.80, "Chi_Tieu_Tuyen_Dung_2026": 3},
        {"Phong_Ban": "An_Ninh_Mang_SecOps", "Nhan_Su_Dau_Nam": 14, "Nhan_Su_Cuoi_Nam": 22, "Ty_Le_Bien_Dong_Percent": 3.0, "Diem_KPI_TB": 4.92, "Chi_Tieu_Tuyen_Dung_2026": 8},
    ]

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame(data_tong_quan).to_excel(writer, sheet_name="Tong_Quan", index=False)
        pd.DataFrame(data_thi_truong).to_excel(writer, sheet_name="Thi_Truong_Kenh_Ban", index=False)
        pd.DataFrame(data_chi_phi).to_excel(writer, sheet_name="Chi_Phi_Van_Hanh", index=False)
        pd.DataFrame(data_kpi).to_excel(writer, sheet_name="KPI_Nhan_Su", index=False)

    print(f"Excel workbook created successfully with 4 sheets.")


def generate_docx_data():
    docx_path = RAW_DOCS_DIR / "chinh_sach_nhan_su_va_van_hanh_2025.docx"
    print(f"Creating Word document: {docx_path}...")

    doc = docx.Document()

    # Title
    title = doc.add_paragraph()
    run = title.add_run("QUY ĐỊNH VẬN HÀNH VÀ CHÍNH SÁCH NHÂN SỰ TẬP ĐOÀN 2025")
    run.bold = True
    run.font.size = Pt(18)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph()
    sub_run = sub.add_run("Mã văn bản: HD-HR-2025/v4.2 | Hiệu lực thi hành: 01/01/2025 | Phạm vi: Toàn bộ cán bộ nhân viên")
    sub_run.italic = True
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("-" * 60)

    # Mục 1
    doc.add_heading("1. QUY CHẾ LÀM VIỆC VÀ THỜI GIAN LÀM VIỆC", level=1)
    
    doc.add_heading("1.1 Khung giờ làm việc tiêu chuẩn và Thời gian cốt lõi (Core Hours)", level=2)
    doc.add_paragraph(
        "Tập đoàn áp dụng tuần làm việc 5 ngày từ Thứ Hai đến Thứ Sáu (nghỉ Thứ Bảy và Chủ Nhật). "
        "Tổng thời gian làm việc tiêu chuẩn là 40 giờ/tuần. "
        "Khung giờ làm việc linh hoạt từ 08:30 đến 18:00 hàng ngày. "
        "Tất cả cán bộ nhân viên bắt buộc phải có mặt hoặc trực tuyến trong hai khung giờ làm việc cốt lõi (Core Hours): "
        "Buổi sáng từ 09:30 đến 11:30 và buổi chiều từ 14:00 đến 16:30 để phục vụ họp điều phối dự án và trao đổi liên phòng ban."
    )

    doc.add_heading("1.2 Chính sách làm việc kết hợp linh hoạt (Hybrid Working)", level=2)
    doc.add_paragraph(
        "Nhân viên sau khi vượt qua giai đoạn thử việc chính thức có quyền đăng ký tối đa 02 ngày làm việc từ xa (Work from Home - WFH) mỗi tuần. "
        "Nhân viên cần đăng ký lịch WFH trên cổng thông tin nội bộ trước 24 giờ và được Quản lý trực tiếp (Line Manager) phê duyệt. "
        "Trong thời gian WFH, nhân viên cam kết đảm bảo đường truyền Internet ổn định, phản hồi tin nhắn Slack/Teams trong vòng tối đa 15 phút "
        "và bật camera khi tham gia các cuộc họp trực tuyến của công ty."
    )

    doc.add_heading("1.3 Chế độ nghỉ phép năm và phép đặc biệt", level=2)
    doc.add_paragraph(
        "Mỗi nhân viên chính thức được hưởng 12 ngày nghỉ phép năm hưởng nguyên lương. "
        "Cứ sau mỗi 03 năm làm việc liên tục tại Tập đoàn, nhân viên được cộng thêm 01 ngày phép năm thâm niên (tối đa không quá 20 ngày phép/năm). "
        "Số ngày phép chưa sử dụng hết trong năm tài chính được phép bảo lưu sang năm tiếp theo và phải sử dụng trước ngày 31 tháng 03 của năm sau. "
        "Ngoài ra, Tập đoàn cấp 03 ngày nghỉ phép nguyên lương nhân dịp kết hôn của nhân viên và 01 ngày phép ngày sinh nhật."
    )

    # Mục 2
    doc.add_heading("2. CHÍNH SÁCH LƯƠNG, THƯỞNG VÀ CHẾ ĐỘ PHÚC LỢI", level=1)

    doc.add_heading("2.1 Chu kỳ đánh giá hiệu suất và điều chỉnh lương định kỳ", level=2)
    doc.add_paragraph(
        "Tập đoàn tiến hành đánh giá hiệu suất nhân sự định kỳ 02 lần trong năm vào Tháng 4 và Tháng 10. "
        "Thang điểm đánh giá hiệu suất từ 1.0 đến 5.0 (Xuất sắc: >= 4.75; Tốt: 4.25 - 4.74; Đạt: 3.5 - 4.24; Cần cải thiện: < 3.5). "
        "Tỷ lệ tăng lương trung bình định kỳ là từ 8% đến 18% tùy theo kết quả xếp loại hiệu suất và đóng góp sáng kiến cho doanh nghiệp."
    )

    doc.add_heading("2.2 Thưởng hiệu quả kinh doanh và Thưởng tháng lương thứ 13", level=2)
    doc.add_paragraph(
        "Toàn bộ nhân viên có thời gian làm việc từ đủ 06 tháng trở lên được nhận lương tháng thứ 13 (chi trả vào kỳ lương trước Tết Nguyên Đán). "
        "Đối với các khối trực tiếp tạo doanh thu (Khối Công nghệ SaaS, Viện AI, Khối B2B), nhân viên được nhận thêm quỹ thưởng KPI dự án "
        "dao động từ 1.5 đến 4.0 tháng lương căn cứ trên tỷ lệ vượt chỉ tiêu lợi nhuận năm."
    )

    doc.add_heading("2.3 Chế độ bảo hiểm sức khỏe nâng cao PVI Care", level=2)
    doc.add_paragraph(
        "Bên cạnh Bảo hiểm Y tế bắt buộc theo Luật Lao động, Tập đoàn tài trợ 100% chi phí gói Bảo hiểm Chăm sóc Sức khỏe Quốc tế PVI Care "
        "với hạn mức bảo lãnh viện phí lên tới 150.000.000 VNĐ/năm/nhân viên, bao gồm điều trị nội trú, ngoại trú, và chăm sóc nha khoa. "
        "Nhân sự có thâm niên từ 03 năm trở lên hoặc giữ vị trí từ Trưởng nhóm (Lead) được tài trợ thêm 50% chi phí bảo hiểm cho 01 người thân."
    )

    # Mục 3
    doc.add_heading("3. CHƯƠNG TRÌNH ĐÀO TẠO VÀ PHÁT TRIỂN NĂNG LỰC", level=1)
    doc.add_paragraph(
        "Tập đoàn cấp ngân sách đào tạo cá nhân lên tới 25.000.000 VNĐ/năm cho mỗi kỹ sư và chuyên viên. "
        "Công ty thanh toán 100% lệ phí thi và cấp thưởng 5.000.000 VNĐ cho mỗi chứng chỉ quốc tế uy tín đạt được, bao gồm: "
        "Google Cloud Professional Data Engineer, AWS Certified Solutions Architect Professional, PMP, CFA Level 2 trở lên. "
        "Nhân sự nhận hỗ trợ chi phí đào tạo trên 20.000.000 VNĐ cam kết tiếp tục làm việc tại Tập đoàn tối thiểu 12 tháng kể từ ngày nhận chứng chỉ."
    )

    # Mục 4
    doc.add_heading("4. QUY TRÌNH THỬ VIỆC VÀ THỦ TỤC THÔI VIỆC", level=1)
    doc.add_paragraph(
        "Thời gian thử việc tiêu chuẩn là 60 ngày đối với vị trí kỹ sư, chuyên viên nghiên cứu và quản lý; 30 ngày đối với vị trí hỗ trợ nghiệp vụ. "
        "Trong thời gian thử việc, mức lương được chi trả bằng 85% đến 100% lương chính thức theo thỏa thuận trong thư mời nhận việc. "
        "Về thời hạn thông báo nghỉ việc: Cán bộ nhân viên ký Hợp đồng lao động không xác định thời hạn phải gửi đơn xin thôi việc bằng văn bản "
        "trước ít nhất 45 ngày; Hợp đồng lao động xác định thời hạn phải báo trước ít nhất 30 ngày. "
        "Nhân viên có nghĩa vụ bàn giao toàn bộ mã nguồn, tài liệu thiết kế, tài khoản phân quyền và thiết bị máy tính cho Quản lý dự án "
        "trước khi ký biên bản thanh lý hợp đồng."
    )

    # Mục 5
    doc.add_heading("5. BẢO MẬT THÔNG TIN VÀ AN TOÀN DỮ LIỆU", level=1)
    doc.add_paragraph(
        "Tất cả nhân viên bắt buộc tuân thủ thỏa thuận bảo mật thông tin (NDA). "
        "Nghiêm cấm tuyệt đối hành vi sao chép dữ liệu khách hàng, mã nguồn dự án, dữ liệu đào tạo AI ra các thiết bị lưu trữ cá nhân "
        "(như USB, ổ cứng ngoài, Google Drive cá nhân). "
        "Bắt buộc cài đặt xác thực 2 yếu tố (2FA) và phần mềm phòng chống mã độc trên mọi máy tính xách tay do Tập đoàn cấp phát. "
        "Mọi hành vi vi phạm bảo mật dữ liệu cấp độ nghiêm trọng sẽ bị xử lý sa thải ngay lập tức và chuyển hồ sơ sang cơ quan bảo vệ pháp luật."
    )

    # Bảng tóm tắt
    doc.add_heading("6. BẢNG TỔNG HỢP CÁC CHỈ SỐ VÀ QUY ĐỊNH CỐT LÕI", level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Hạng mục"
    hdr_cells[1].text = "Quy định / Định mức"
    hdr_cells[2].text = "Đối tượng áp dụng"
    hdr_cells[3].text = "Bộ phận phụ trách"

    table_data = [
        ("Thời gian làm việc cốt lõi", "09:30 - 11:30 & 14:00 - 16:30", "Toàn bộ nhân viên", "Quản lý trực tiếp"),
        ("Hạn mức WFH", "Tối đa 02 ngày/tuần", "Nhân viên chính thức", "Line Manager & HR"),
        ("Ngày nghỉ phép năm", "12 ngày/năm (+1 ngày mỗi 3 năm)", "Nhân viên chính thức", "Phòng Nhân sự"),
        ("Hạn mức bảo hiểm PVI", "150.000.000 VNĐ/năm", "Nhân viên chính thức", "Phòng Nhân sự"),
        ("Ngân sách chứng chỉ quốc tế", "Lên tới 25.000.000 VNĐ/năm", "Khối Công nghệ & Phân tích", "Ban Đào tạo"),
        ("Thời hạn báo trước thôi việc", "45 ngày (HĐ KTH) / 30 ngày (HĐ CTH)", "Toàn thể cán bộ nhân viên", "Phòng Nhân sự"),
        ("Chu kỳ đánh giá lương", "Tháng 4 và Tháng 10 hàng năm", "Toàn bộ nhân viên", "Ban Giám đốc & HR"),
    ]

    for row_item in table_data:
        row_cells = table.add_row().cells
        for i, val in enumerate(row_item):
            row_cells[i].text = str(val)

    doc.save(docx_path)
    print(f"Word document created successfully: {docx_path}")


if __name__ == "__main__":
    generate_excel_data()
    generate_docx_data()
