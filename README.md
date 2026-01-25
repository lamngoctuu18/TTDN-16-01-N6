<h2 align="center">
    <a href="https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin">
    🎓 Faculty of Information Technology (DaiNam University)
    </a>
</h2>
<h2 align="center">
    PLATFORM ERP
</h2>
<div align="center">
    <p align="center">
        <img src="docs/logo/aiotlab_logo.png" alt="AIoTLab Logo" width="170"/>
        <img src="docs/logo/fitdnu_logo.png" alt="AIoTLab Logo" width="180"/>
        <img src="docs/logo/dnu_logo.png" alt="DaiNam University Logo" width="200"/>
    </p>

[![AIoTLab](https://img.shields.io/badge/AIoTLab-green?style=for-the-badge)](https://www.facebook.com/DNUAIoTLab)
[![Faculty of Information Technology](https://img.shields.io/badge/Faculty%20of%20Information%20Technology-blue?style=for-the-badge)](https://dainam.edu.vn/vi/khoa-cong-nghe-thong-tin)
[![DaiNam University](https://img.shields.io/badge/DaiNam%20University-orange?style=for-the-badge)](https://dainam.edu.vn)

</div>

## 📖 1. Giới thiệu
Platform ERP được áp dụng vào học phần Thực tập doanh nghiệp dựa trên mã nguồn mở Odoo. 

## 🔧 2. Các công nghệ được sử dụng
<div align="center">

### Hệ điều hành
[![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com/)
### Công nghệ chính
[![Odoo](https://img.shields.io/badge/Odoo-714B67?style=for-the-badge&logo=odoo&logoColor=white)](https://www.odoo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![XML](https://img.shields.io/badge/XML-FF6600?style=for-the-badge&logo=codeforces&logoColor=white)](https://www.w3.org/XML/)
### Cơ sở dữ liệu
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
</div>

## 🧩 3. Các phân hệ đã phát triển

### 3.1. Quản lý Tài sản & Phòng họp (dnu_meeting_asset)
Phân hệ quản lý toàn bộ vòng đời tài sản và điều phối lịch sử dụng phòng họp.

**Chức năng chính:**
- Danh mục tài sản, mã tài sản, vị trí, phòng họp, trạng thái tài sản.
- Gán tài sản cho nhân viên và theo dõi lịch sử gán.
- Mượn/Trả tài sản và theo dõi quá hạn.
- Bảo trì tài sản: tạo yêu cầu, theo dõi tiến độ, lịch bảo trì định kỳ.
- Biên bản bàn giao, kiểm kê, khấu hao và thanh lý tài sản.
- Dashboard tổng quan và báo cáo.
- Quản lý phòng họp, đặt lịch, kiểm tra xung đột và check-in/check-out.
- **AI hỗ trợ**: gợi ý bảo trì, phân tích nhanh thông tin tài sản/phòng họp (tích hợp OpenAI).
- **Tự động hóa**: nhắc lịch, tự động cập nhật trạng thái, xử lý quá hạn theo lịch tác vụ.
- **Tích hợp lịch**: đồng bộ lịch họp với Calendar.
- **Tích hợp họp trực tuyến**: kết nối Zoom cho lịch họp.

### 3.2. Quản lý Nhân sự (nhan_su)
Phân hệ quản lý thông tin nhân sự và cấu trúc tổ chức.

**Chức năng chính:**
- Danh mục chức vụ.
- Đơn vị/phòng ban.
- Hồ sơ nhân viên.
- Lịch sử công tác.
- Chứng chỉ/bằng cấp và danh sách chứng chỉ.
- Phân quyền truy cập theo vai trò.

### 3.3. Quản lý Văn bản (quan_ly_van_ban)
Phân hệ quản lý luồng văn bản đến/đi trong nội bộ.

**Chức năng chính:**
- Văn bản đến.
- Văn bản đi.
- Loại văn bản và danh mục liên quan.
- Liên kết văn bản với nhân viên/đơn vị.
- Cơ chế phân quyền và lịch nhắc việc theo tác vụ định kỳ.

### 3.4. Tích hợp giữa các phân hệ
- Tài sản được gán cho nhân sự và hiển thị lịch sử gán theo nhân viên.
- Văn bản liên kết nhân sự/đơn vị để thuận tiện theo dõi xử lý.
- Tài sản & phòng họp tích hợp với nhân sự và văn bản trong cùng hệ thống.
- AI và tự động hóa hỗ trợ thống nhất quy trình xử lý tài sản, lịch họp và văn bản.

### 3.5. Sơ đồ nghiệp vụ (Business Flow)
Ghi chú: Các sơ đồ bên dưới dùng Mermaid (GitHub/GitLab hỗ trợ hiển thị trực tiếp trong Markdown).

#### 3.5.1. Vòng đời tài sản (Asset Lifecycle)
```mermaid
flowchart LR
    A[Tạo tài sản] --> B{Trạng thái}
    B -->|Sẵn sàng| C[Sử dụng nội bộ]
    C --> D[Gán cho nhân viên]
    D --> E[Thu hồi / Luân chuyển]
    E --> B
    B -->|Đang mượn| F[Mượn/Trả tài sản]
    F --> B
    B -->|Bảo trì| G[Tạo yêu cầu bảo trì]
    G --> H[Thực hiện/Hoàn thành]
    H --> B
    B -->|Thanh lý| I[Đề xuất / Phê duyệt]
    I --> J[Thanh lý / Ghi nhận]
    J --> K[Đã thanh lý]
```

#### 3.5.2. Quy trình mượn/trả tài sản (Lending)
```mermaid
flowchart TD
    U[Người dùng tạo phiếu mượn] --> V[Chọn tài sản + thời hạn]
    V --> W{Tài sản khả dụng?}
    W -->|Không| X[Thông báo không khả dụng]
    W -->|Có| Y[Phê duyệt/ Xác nhận]
    Y --> Z[Đang mượn]
    Z --> AA{Đến hạn?}
    AA -->|Đúng| AB[Tự động đánh dấu quá hạn + nhắc trả]
    AA -->|Chưa| Z
    Z --> AC[Trả tài sản]
    AB --> AC
    AC --> AD[Hoàn tất + cập nhật trạng thái tài sản]
```

#### 3.5.3. Quy trình bảo trì + tự động hóa (Maintenance & Automation)
```mermaid
flowchart TD
    M[Phát sinh sự cố / lịch định kỳ] --> N[Tạo yêu cầu bảo trì]
    N --> O[Phân công kỹ thuật viên]
    O --> P[Đang xử lý]
    P --> Q{Hoàn thành?}
    Q -->|Chưa| P
    Q -->|Có| R[Hoàn thành + cập nhật tài sản]
    S[Cron: Nhắc lịch bảo trì] --> N
    T[Cron: Nhắc quá hạn mượn] --> AB[Thông báo quá hạn]
```

#### 3.5.4. Đặt phòng họp + Calendar + Zoom
```mermaid
flowchart TD
    A1[Người dùng tạo booking] --> A2[Chọn phòng + thời gian + người tham dự]
    A2 --> A3{Kiểm tra xung đột}
    A3 -->|Có xung đột| A4[Gợi ý phòng/khung giờ khác]
    A4 --> A2
    A3 -->|Không| A5[Xác nhận booking]
    A5 --> A6[Gửi email xác nhận]
    A5 --> A7[Đồng bộ sự kiện Calendar]
    A5 --> A8[Tạo/đính kèm Zoom meeting]
    A9[Check-in/Check-out] --> A10[Cập nhật trạng thái booking]
```

#### 3.5.5. Quản lý văn bản đến/đi (Document Flow)
```mermaid
flowchart TD
    D1[Văn bản đến] --> D2[Tiếp nhận + phân loại]
    D2 --> D3[Phân công xử lý (nhân viên/đơn vị)]
    D3 --> D4[Theo dõi tiến độ/nhắc việc (cron)]
    D4 --> D5[Hoàn tất + lưu trữ]

    E1[Văn bản đi] --> E2[Soạn thảo]
    E2 --> E3[Duyệt/ban hành]
    E3 --> E4[Phát hành + lưu trữ]
```

#### 3.5.6. Nhân sự (HR Core)
```mermaid
flowchart TD
    H1[Tạo đơn vị/phòng ban] --> H2[Tạo chức vụ]
    H2 --> H3[Tạo hồ sơ nhân viên]
    H3 --> H4[Cập nhật lịch sử công tác]
    H3 --> H5[Quản lý chứng chỉ/bằng cấp]
    H6[Phân quyền người dùng] --> H3
```

## 🚀 4. Các project đã thực hiện dựa trên Platform

Một số project sinh viên đã thực hiện:
- #### [Khoá 15](./docs/projects/K15/README.md)
- #### [Khoá 16]() (Coming soon)
## ⚙️ 5. Cài đặt

### 5.1. Cài đặt công cụ, môi trường và các thư viện cần thiết

#### 5.1.1. Tải project.
```
git clone https://gitlab.com/anhlta/odoo-fitdnu.git
```
#### 5.1.2. Cài đặt các thư viện cần thiết
Người sử dụng thực thi các lệnh sau đề cài đặt các thư viện cần thiết

```
sudo apt-get install libxml2-dev libxslt-dev libldap2-dev libsasl2-dev libssl-dev python3.10-distutils python3.10-dev build-essential libssl-dev libffi-dev zlib1g-dev python3.10-venv libpq-dev
```
#### 5.1.3. Khởi tạo môi trường ảo.
- Khởi tạo môi trường ảo
```
python3.10 -m venv ./venv
```
- Thay đổi trình thông dịch sang môi trường ảo
```
source venv/bin/activate
```
- Chạy requirements.txt để cài đặt tiếp các thư viện được yêu cầu
```
pip3 install -r requirements.txt
```
### 5.2. Setup database

Khởi tạo database trên docker bằng việc thực thi file dockercompose.yml.
```
sudo docker-compose up -d
```
### 5.3. Setup tham số chạy cho hệ thống
Tạo tệp **odoo.conf** có nội dung như sau:
```
[options]
addons_path = addons
db_host = localhost
db_password = odoo
db_user = odoo
db_port = 5431
xmlrpc_port = 8069
```
Có thể kế thừa từ file **odoo.conf.template**
### 5.4. Chạy hệ thống và cài đặt các ứng dụng cần thiết
Lệnh chạy
```
python3 odoo-bin.py -c odoo.conf -u all
```
Người sử dụng truy cập theo đường dẫn _http://localhost:8069/_ để đăng nhập vào hệ thống.

## 📝 6. License

© 2024 AIoTLab, Faculty of Information Technology, DaiNam University. All rights reserved.

---

    
