# DNU Meeting & Asset Management

## 📋 Tổng quan

Module **Quản lý Tài sản và Phòng họp** được phát triển cho Odoo v15, tích hợp với module Nhân sự (HR) để quản lý toàn diện tài sản công ty và lịch đặt phòng họp.

**Nhóm phát triển:** Sinh viên FIT-DNU  
**Đề tài:** BTL Thực tập - Đề 6: Quản lý tài sản + Phòng họp

---

## ✨ Tính năng chính

### 🏢 Quản lý Tài sản
- ✅ Quản lý danh mục tài sản (cây phân cấp)
- ✅ Quản lý tài sản: thiết bị, máy móc, đồ dùng văn phòng
- ✅ Theo dõi trạng thái: Sẵn sàng / Đã gán / Bảo trì / Đã thanh lý
- ✅ Gán tài sản cho nhân viên với lịch sử đầy đủ
- ✅ Quản lý bảo trì và sửa chữa (ticket system)
- ✅ Tính toán giá trị hiện tại (khấu hao)
- ✅ Mã vạch / QR code cho tài sản

### 🏛️ Quản lý Phòng họp
- ✅ Quản lý phòng họp với thông tin chi tiết (sức chứa, vị trí, tiện nghi)
- ✅ Đặt phòng với giao diện Calendar trực quan
- ✅ **Tự động kiểm tra xung đột** khi đặt phòng
- ✅ Gợi ý phòng thay thế khi có xung đột
- ✅ Check-in/Check-out vào phòng
- ✅ Tích hợp với Calendar (đồng bộ Google Calendar)
- ✅ Gửi email tự động: Xác nhận / Hủy / Nhắc nhở

### 🔐 Phân quyền
- **Asset User**: Xem tài sản, tạo yêu cầu bảo trì
- **Asset Manager**: Quản lý tài sản, gán cho nhân viên
- **Meeting User**: Đặt phòng họp
- **Meeting Manager**: Duyệt/hủy booking
- **Facility Staff**: Quyền đầy đủ

### 🚀 API REST
- Danh sách phòng họp
- Kiểm tra khả dụng phòng
- Lấy khung giờ còn trống
- Tạo/hủy booking
- Check-in/Check-out
- Quản lý tài sản

---

## 📦 Cài đặt

### Yêu cầu
- Odoo 15.0
- Python 3.8+
- Module dependencies: `base`, `hr`, `calendar`, `mail`

### Các bước cài đặt

1. **Copy module vào thư mục addons:**
   ```bash
   cp -r dnu_meeting_asset /path/to/odoo/addons/
   ```

2. **Cập nhật danh sách apps:**
   - Vào Odoo: Settings → Apps → Update Apps List

3. **Cài đặt module:**
   - Tìm "DNU Meeting & Asset Management"
   - Click "Install"

4. **Cấu hình (tùy chọn):**
   - Settings → Users & Companies → Users
   - Gán quyền cho users: Asset Manager, Meeting Manager, v.v.

---

## 🎯 Hướng dẫn sử dụng

### Quản lý Tài sản

#### 1. Tạo danh mục tài sản
```
Asset & Meeting → Quản lý tài sản → Danh mục
- Tạo các danh mục: Thiết bị điện tử, IT, Nội thất...
- Có thể tạo cây phân cấp
```

#### 2. Thêm tài sản mới
```
Asset & Meeting → Quản lý tài sản → Tài sản → Create
- Nhập: Tên, Danh mục, Serial, Giá trị mua...
- Mã tài sản tự động: AST00001, AST00002...
```

#### 3. Gán tài sản cho nhân viên
```
Mở tài sản → Click "Gán cho nhân viên"
- Chọn nhân viên
- Ngày bắt đầu / kết thúc
- Lưu lịch sử đầy đủ
```

#### 4. Tạo yêu cầu bảo trì
```
Mở tài sản → Click "Tạo yêu cầu bảo trì"
- Mô tả sự cố
- Độ ưu tiên: Thấp / Bình thường / Cao / Khẩn cấp
- Gán kỹ thuật viên
```

### Quản lý Phòng họp

#### 1. Tạo phòng họp
```
Asset & Meeting → Quản lý phòng họp → Phòng họp → Create
- Tên phòng, Mã phòng, Sức chứa
- Vị trí, Tầng, Toà nhà
- Tích chọn tiện nghi: Máy chiếu, TV, Whiteboard...
```

#### 2. Đặt phòng họp
```
Asset & Meeting → Quản lý phòng họp → Đặt phòng → Create

Cách 1: Từ Calendar View
- Click vào ngày/giờ muốn đặt
- Chọn phòng, nhập chủ đề
- Thêm người tham dự

Cách 2: Từ Form
- Chọn phòng, thời gian
- Hệ thống tự động kiểm tra xung đột
- Nếu OK → Click "Gửi yêu cầu" hoặc "Xác nhận"
```

#### 3. Check-in vào phòng
```
- Mở booking
- Click "Check-in" (15 phút trước giờ họp)
- Hệ thống ghi lại thời gian check-in
```

#### 4. Xử lý xung đột
```
Nếu có xung đột:
- Thông báo màu đỏ hiện ra
- Click "Gợi ý phòng khác"
- Chọn phòng phù hợp từ danh sách
```

---

## 🔌 API Documentation

Base URL: `http://your-odoo-instance.com/api`

### Authentication
Tất cả API yêu cầu authentication với Odoo session.

### Endpoints

#### 1. Lấy danh sách phòng họp
```http
POST /api/meeting/rooms
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "params": {
    "state": "available",
    "capacity_min": 10
  }
}
```

#### 2. Kiểm tra khả dụng phòng
```http
POST /api/meeting/rooms/<room_id>/availability
{
  "jsonrpc": "2.0",
  "params": {
    "start_datetime": "2024-01-10T09:00:00",
    "end_datetime": "2024-01-10T11:00:00"
  }
}
```

#### 3. Tạo booking
```http
POST /api/meeting/bookings
{
  "jsonrpc": "2.0",
  "params": {
    "room_id": 1,
    "subject": "Team Meeting",
    "start_datetime": "2024-01-10T14:00:00",
    "end_datetime": "2024-01-10T15:00:00",
    "attendee_ids": [1, 2, 3]
  }
}
```

#### 4. Check-in
```http
POST /api/meeting/bookings/<booking_id>/checkin
```

Chi tiết đầy đủ: Xem file `controllers/main.py`

---

## 📊 Báo cáo

### Báo cáo tài sản
```
Asset & Meeting → Báo cáo → Báo cáo tài sản
- Thống kê theo danh mục
- Phân tích trạng thái
- Giá trị tài sản
```

### Thống kê đặt phòng
```
Asset & Meeting → Báo cáo → Thống kê đặt phòng
- Tỷ lệ sử dụng phòng
- Booking theo thời gian
- Phòng được đặt nhiều nhất
```

---

## ⚙️ Cấu hình nâng cao

### Email Templates
Tùy chỉnh email tại:
```
Settings → Technical → Email → Email Templates
- Meeting Booking: Confirmation
- Meeting Booking: Cancellation
- Meeting Booking: Reminder
```

### Cron Jobs (Tự động hóa)
```
Settings → Technical → Automation → Scheduled Actions
- Auto Checkout: 15 phút/lần
- Send Reminders: 10 phút/lần
```

### Sequences
Tùy chỉnh format mã tại:
```
Settings → Technical → Sequences & Identifiers → Sequences
- dnu.asset: AST00001
- dnu.meeting.booking: BOOK00001
- dnu.asset.maintenance: MNT00001
```

---

## 🛠️ Phát triển & Mở rộng

### Cấu trúc thư mục
```
dnu_meeting_asset/
├── models/
│   ├── dnu_asset.py
│   ├── dnu_asset_category.py
│   ├── dnu_asset_assignment.py
│   ├── dnu_asset_maintenance.py
│   ├── dnu_meeting_room.py
│   └── dnu_meeting_booking.py
├── views/
│   ├── dnu_asset_views.xml
│   ├── dnu_meeting_room_views.xml
│   ├── dnu_meeting_booking_views.xml
│   └── menu_views.xml
├── controllers/
│   └── main.py
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
├── data/
│   ├── sequence_data.xml
│   ├── mail_template.xml
│   └── cron.xml
└── __manifest__.py
```

### Tích hợp AI (Gợi ý)

#### 1. Auto-suggest Room
```python
def suggest_best_room(self, num_people, required_equipment, datetime):
    # ML model để gợi ý phòng tốt nhất
    # Dựa trên lịch sử, số người, thiết bị
    pass
```

#### 2. Predictive Maintenance
```python
def predict_maintenance_needed(self, asset):
    # Dự báo tài sản cần bảo trì
    # Dựa trên lịch sử sử dụng, thời gian
    pass
```

#### 3. Natural Language Booking
```python
def parse_booking_request(self, text):
    # "Đặt phòng 10 người ngày mai 2h chiều"
    # LLM parse ra: num_people=10, datetime=...
    pass
```

---

## 🧪 Testing

### Demo Data
Module có sẵn demo data:
- 3 danh mục tài sản
- 2 tài sản mẫu
- 3 phòng họp

### Test Cases
1. Tạo tài sản → Gán cho nhân viên → Trả lại
2. Đặt phòng → Xung đột → Chọn phòng khác
3. Check-in → Check-out
4. Tạo bảo trì → Xử lý → Hoàn thành

---

## 📝 Changelog

### Version 1.0.0 (2025-01-05)
- ✅ Phát hành phiên bản đầu tiên
- ✅ Quản lý tài sản đầy đủ
- ✅ Quản lý phòng họp & booking
- ✅ Tích hợp HR
- ✅ REST API
- ✅ Email notifications
- ✅ Conflict detection

---

## 🤝 Đóng góp

Đây là dự án BTL của nhóm sinh viên FIT-DNU. Mọi đóng góp xin gửi về:
- GitHub Repository: [Link repo của khoa]
- Email: [Email nhóm]

---

## 📄 License

LGPL-3 - Xem file LICENSE để biết chi tiết

---

## 👥 Nhóm phát triển

- **Thành viên 1**: [Tên] - [Vai trò]
- **Thành viên 2**: [Tên] - [Vai trò]
- **Thành viên 3**: [Tên] - [Vai trò]

**Giảng viên hướng dẫn**: [Tên GV]

---

## 🔗 Tài liệu tham khảo

- [Odoo 15 Documentation](https://www.odoo.com/documentation/15.0/)
- [Odoo Development Tutorials](https://www.odoo.com/documentation/15.0/developer.html)
- [Python API Reference](https://www.odoo.com/documentation/15.0/developer/reference/backend.html)

---

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra log Odoo: `/var/log/odoo/odoo-server.log`
2. Kiểm tra console trình duyệt (F12)
3. Liên hệ nhóm phát triển

---

**🎉 Chúc bạn sử dụng module thành công!**
