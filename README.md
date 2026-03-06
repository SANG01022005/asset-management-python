# Asset Management API System (Python)
Dự án này là hệ thống quản lý tài sản số (Assets) được xây dựng bằng ngôn ngữ Python và framework FastAPI. Mã nguồn được tổ chức chặt chẽ theo kiến trúc Clean Architecture, giúp tách biệt rõ ràng giữa logic nghiệp vụ, giao diện lập trình và hạ tầng kỹ thuật.

# Cấu trúc thư mục (Project Structure)
```
asset-management-python/
├── app/
│   ├── api/            # Giao diện lập trình (Controllers/Routers)
│   │   ├── assets.py   # Quản lý CRUD, Batch operations, Search, Pagination
│   │   └── health.py   # Kiểm tra sức khỏe hệ thống & Database connection
│   ├── domain/         # Nghiệp vụ cốt lõi (Entities & Validation)
│   │   ├── models.py   # Định nghĩa SQLAlchemy ORM Models
│   │   └── schemas.py  # Định nghĩa Pydantic Schemas (DTOs)
│   ├── infrastructure/ # Hạ tầng kỹ thuật
│   │   └── database.py # Cấu hình kết nối DB & cơ chế Retry (Exponential Backoff)
│   └── usecases/       # Logic xử lý nghiệp vụ phức tạp
├── homeworks/
│   └── submissions/    # Minh chứng kết quả thực hiện bài tập (Command outputs)
├── venv/               # Môi trường ảo Python (Virtual Environment)
├── .env                # Biến môi trường (DATABASE_URL,...)
├── .env.example        # File mẫu cấu hình biến môi trường
├── .gitignore          # Cấu hình các file không đẩy lên Git (venv, .env)
├── main.py             # Điểm chạy ứng dụng (Entry point)
├── README.md           # Hướng dẫn dự án
└── requirements.txt    # Danh sách các thư viện cần thiết
```
# Hướng dẫn cài đặt và khởi chạy
1. Chuẩn bị Cơ sở dữ liệu (PostgreSQL)
Có thể chạy Database nhanh chóng thông qua Docker:
docker compose up -d
Hoặc nếu sử dụng PostgreSQL cài trực tiếp trên máy, hãy đảm bảo đã tạo database tên là asset_management với port 5432.

2. Thiết lập môi trường Python
Dự án sử dụng môi trường ảo để quản lý thư viện độc lập.

# 1. Kích hoạt môi trường ảo (Windows)
.\venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 3. Cấu hình biến môi trường
# Copy file .env.example thành .env và chỉnh sửa DATABASE_URL nếu cần
cp .env.example .env
3. Khởi chạy ứng dụng
python main.py
Sau khi khởi chạy thành công, hệ thống sẽ tự động tạo các bảng cần thiết trong Database. Bạn có thể truy cập tài liệu API tại:

Swagger UI: http://localhost:8080/docs

🧪 Quy trình kiểm thử và Nộp bài (Submission)
Toàn bộ các yêu cầu bài tập từ Bài 1 đến Bài 7 (bao gồm các phần Bonus) đều đã được thực hiện và kiểm chứng:

Minh chứng kết quả: Các file log và command output chi tiết cho từng bài tập được lưu trữ tại thư mục homeworks/submissions/.

Các tính năng nổi bật:

Batch Operations: Hỗ trợ tạo và xóa hàng loạt tài sản trong một Transaction (nguyên tử).

Connection Retry: Cơ chế tự động thử lại kết nối khi Database gặp sự cố.

Pagination & Search: Phân trang linh hoạt và tìm kiếm tài sản theo tên (không phân biệt hoa thường).