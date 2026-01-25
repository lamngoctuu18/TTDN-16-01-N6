# 🏠 TRUNG TÂM QUẢN LÝ TÀI SẢN - HƯỚNG DẪN SỬ DỤNG

## Tổng quan
**Trung tâm quản lý tài sản** là giao diện tổng hợp hiện đại, tích hợp 7 chức năng chính vào 1 màn hình duy nhất với theme màu **Cam đậm (#E67E22)** và **Xanh dương (#2980B9)**.

---

## 🎯 Tính năng chính

### 1. Dashboard KPI (8 thẻ thống kê)
- **Tổng tài sản** - Tổng số tài sản trong hệ thống
- **Sẵn sàng** - Tài sản có thể gán/mượn ngay
- **Đang gán** - Tài sản đã gán cho nhân viên cố định
- **Đang mượn** - Tài sản đang được mượn
- **Quá hạn** - Phiếu mượn đã quá hạn trả
- **Đang bảo trì** - Tài sản đang trong quá trình bảo trì
- **Biên bản chờ ký** - Biên bản ở trạng thái draft/pending_signature
- **Bảo trì sắp tới** - Lịch bảo trì định kỳ trong 7 ngày tới

💡 **Click vào KPI card** để xem chi tiết module tương ứng

---

### 2. Quick Actions (Thanh công cụ nhanh)
Các nút tạo nhanh ở header:
- 🆕 **Tạo tài sản** - Thêm tài sản mới
- 🤝 **Tạo phiếu mượn** - Tạo yêu cầu mượn tài sản
- 📋 **Tạo biên bản** - Lập biên bản bàn giao
- 🔧 **Tạo bảo trì** - Ghi nhận sự cố/bảo trì
- 📅 **Lập lịch định kỳ** - Thiết lập bảo trì tự động

---

### 3. Navigation Tabs (7 mục chính)

#### 📦 **Tài sản**
- **View modes**: Kanban, List, Pivot, Graph
- **Searchpanel**: Lọc theo Danh mục, Trạng thái, Vị trí
- **Kanban features**:
  - Card thiết kế gradient cam-xanh
  - Badge trạng thái màu sắc
  - Hiển thị giá trị hiện tại
  - Hover effect nổi lên

#### 📂 **Danh mục**
- Quản lý phân loại tài sản
- Tree view và Form view
- Hỗ trợ cấu trúc cây

#### 👤 **Lịch sử gán**
- Theo dõi tài sản đã gán cho nhân viên
- Lọc theo nhân viên, phòng ban
- Timeline gán/thu hồi

#### 🤝 **Mượn tài sản**
- **View modes**: Kanban (grouped by state), List, Form
- **Searchpanel**: Lọc theo Phòng ban, Trạng thái
- **Kanban features**:
  - Border màu theo trạng thái (Draft/Approved/Borrowed/Overdue/Returned)
  - Badge "QUÁ HẠN" màu đỏ nổi bật
  - Hiển thị ngày mượn/ngày trả dự kiến
- **Workflow**:
  1. Draft → Gửi yêu cầu
  2. Requested → Duyệt
  3. Approved → Tạo biên bản → Giao tài sản
  4. Borrowed → Tạo biên bản trả → Trả tài sản
  5. Returned (hoàn thành)

#### 🔧 **Bảo trì**
- **View modes**: Kanban (grouped by state), List, Calendar, Form
- **Kanban features**:
  - Priority stars (★★★)
  - Type badge (Sửa chữa/Bảo dưỡng/Nâng cấp)
  - Hiển thị kỹ thuật viên
  - Ngày báo cáo & ngày lên lịch
- **Workflow**: Planned → In Progress → Done

#### 📋 **Biên bản bàn giao**
- **View modes**: Kanban (grouped by state), Tree, Form
- **Kanban features**:
  - Badge loại biên bản (GÁN/MƯỢN/TRẢ)
  - Trạng thái chữ ký (✓ hoặc ⏳)
  - Border màu theo state
- **Digital Signature**: Vẽ chữ ký trên canvas
- **Workflow**:
  1. Draft → Gửi để ký
  2. Pending Signature → Người nhận ký + Người giao ký
  3. Signed → Hoàn thành
  4. Completed (tự động tạo văn bản)

#### 📅 **Lịch bảo trì định kỳ**
- **View modes**: Calendar, List, Form
- Tự động tạo maintenance ticket khi đến hạn
- Cron job chạy hàng ngày
- Thiết lập chu kỳ: Hàng ngày/Tuần/Tháng/Năm

---

## 🎨 Theme và Màu sắc

### Màu chính
- **Cam đậm**: `#E67E22` (Primary)
- **Cam đậm tối**: `#D35400` (Gradient end)
- **Xanh dương**: `#2980B9` (Secondary)
- **Xanh dương tối**: `#1F618D` (Gradient end)

### Màu trạng thái
- **Xanh lá**: `#27AE60` - Available, Success
- **Cam**: `#E67E22` - Maintenance, Warning
- **Đỏ**: `#E74C3C` - Overdue, Danger
- **Xanh dương**: `#2980B9` - Assigned, Info
- **Xanh nhạt**: `#3498DB` - On Loan
- **Tím**: `#8E44AD` - Return handover
- **Vàng**: `#F39C12` - Pending signature

---

## 🔍 Searchpanel & Filters

### Tài sản
- **Danh mục** (Category) - Lọc theo loại tài sản
- **Trạng thái** (State) - Multi-select: Available/Assigned/On Loan/Maintenance/Disposed
- **Vị trí** (Location) - Multi-select theo địa điểm

### Mượn tài sản
- **Phòng ban** (Department) - Lọc theo đơn vị
- **Trạng thái** (State) - Multi-select: Draft/Requested/Approved/Borrowed/Overdue/Returned

💡 **Counters** hiển thị số lượng bản ghi tại mỗi mục filter

---

## 🚀 Cách sử dụng

### Bước 1: Mở Trung tâm tài sản
```
Menu: Quản lý tài sản → 🏠 Trung tâm tài sản
```

### Bước 2: Xem tổng quan KPI
- Quan sát 8 thẻ KPI ở phía trên
- Click vào thẻ để xem chi tiết

### Bước 3: Sử dụng Quick Actions
- Tạo nhanh từ thanh header (5 nút)
- Không cần quay lại menu

### Bước 4: Điều hướng qua Tabs
- Chuyển giữa 7 mục bằng Notebook tabs
- Không reload trang

### Bước 5: Sử dụng Searchpanel
- Chọn filter bên trái trong Kanban view
- Counters tự động cập nhật

---

## 💡 Workflow thực tế

### Kịch bản 1: Gán tài sản cho nhân viên mới
1. Click KPI "Sẵn sàng" → Xem tài sản available
2. Chọn tài sản → Click "Gán cho nhân viên"
3. Điền thông tin → "Tạo biên bản"
4. Gửi để ký → Nhân viên ký → Người giao ký
5. Hoàn thành biên bản → "Xác nhận"
6. Tài sản chuyển sang "Đang gán"

### Kịch bản 2: Cho mượn tài sản dùng chung
1. Tab "Mượn tài sản" → "Tạo phiếu mượn"
2. Chọn tài sản + người mượn + ngày trả
3. Gửi yêu cầu → Quản lý duyệt
4. "Tạo biên bản" → Hoàn thành ký
5. "Giao tài sản" → Tài sản chuyển sang "Đang mượn"
6. Đến hạn trả: "Tạo biên bản trả" → Hoàn thành ký
7. "Trả tài sản" → Hệ thống check tình trạng
   - Nếu hư hỏng → Tự động tạo phiếu bảo trì
   - Nếu tốt → Tài sản về "Sẵn sàng"

### Kịch bản 3: Quản lý bảo trì định kỳ
1. Tab "Lịch bảo trì định kỳ" → "Lập lịch định kỳ"
2. Chọn tài sản + Chu kỳ (VD: 3 tháng/lần)
3. Thiết lập kỹ thuật viên mặc định
4. Hệ thống tự động tạo maintenance ticket khi đến hạn
5. Kỹ thuật viên xử lý trong tab "Bảo trì"
6. Đánh dấu "Hoàn thành" → Tài sản về trạng thái cũ

---

## 📊 Tính năng nâng cao

### 1. Auto-create logic
- Giao tài sản mượn → Tự tạo biên bản nếu chưa có
- Trả tài sản mượn → Tự tạo biên bản trả nếu chưa có
- Trả tài sản hư → Tự tạo phiếu bảo trì

### 2. Mandatory handover enforcement
- Không thể xác nhận gán nếu biên bản chưa completed
- Không thể giao tài sản mượn nếu biên bản chưa completed
- Không thể trả tài sản nếu biên bản trả chưa completed

### 3. Smart buttons & navigation
- Từ Tài sản → Xem lịch sử gán/mượn/bảo trì/biên bản
- Từ Bảo trì → Xem lending/assignment gốc
- Từ Assignment/Lending → Mở biên bản tương ứng

### 4. Email reminders
- Tự động nhắc nhở trước hạn trả (configurable)
- Cron job chạy 8:00 sáng hàng ngày
- Chỉ gửi 1 lần để tránh spam

### 5. Document integration
- Biên bản hoàn thành → Tự động tạo văn bản đi
- Liên kết 2 chiều với module quản lý văn bản

---

## 🎨 UI/UX Highlights

### Kanban Cards
- ✨ **Gradient headers** - Cam-xanh gradient đẹp mắt
- 🎯 **Color-coded borders** - Border màu theo trạng thái
- 🚀 **Hover effects** - Transform + shadow khi hover
- 📌 **Badges** - Rounded badges cho type/status
- 📊 **Progress indicators** - Visual progress bars

### Typography
- 🔤 **Font weights**: 700 (bold titles), 600 (semi-bold), 500 (medium)
- 📏 **Sizes**: 16px (titles), 14px (subtitles), 13px (body), 12px (meta), 11px (badges)
- 🎨 **Colors**: `#2C3E50` (dark), `#34495E` (body), `#7F8C8D` (gray)

### Spacing & Layout
- 📐 **Border radius**: 12px (cards), 10px (small cards), 20px (badges)
- 📦 **Padding**: 15px (normal), 12px (compact)
- 📏 **Margins**: 8-12px (vertical), 5-10px (horizontal)
- 🎯 **Box shadows**: `0 2px 8px rgba(0,0,0,0.08)` → `0 6px 20px rgba(0,0,0,0.15)` on hover

---

## 🔧 Khắc phục sự cố

### Không thấy menu "Trung tâm tài sản"
- Upgrade module: `./odoo-bin -c odoo.conf -d btl_nhom6 -u dnu_meeting_asset --stop-after-init`
- Xóa cache trình duyệt: Ctrl+Shift+R

### KPI không cập nhật
- KPI được tính real-time mỗi khi mở dashboard
- Nếu vẫn sai → Check database: `SELECT COUNT(*) FROM dnu_asset WHERE state='available'`

### Searchpanel không hiện
- Check model có field `category_id`, `state`, `location` (tài sản)
- Check model có field `department_id`, `state` (mượn)
- Restart Odoo service

### CSS không load
- Check file: `addons/dnu_meeting_asset/static/src/css/asset_center_theme.css`
- Update assets: Odoo → Settings → Activate developer mode → Debug → Regenerate assets

---

## 📞 Hỗ trợ

Nếu gặp vấn đề, kiểm tra:
1. **Logs**: `tail -f /var/log/odoo/odoo-server.log`
2. **Browser console**: F12 → Console tab
3. **Odoo logs**: Settings → Technical → Logging

---

## 🎉 Tính năng sắp có

- [ ] Export báo cáo Excel từ KPI
- [ ] Biểu đồ tương tác (drill-down)
- [ ] Mobile app view
- [ ] QR code scanning cho tài sản
- [ ] AI suggestions cho bảo trì dự đoán
- [ ] Integration với Teams/Slack notifications

---

**Version**: 1.0.0  
**Last Updated**: January 22, 2026  
**Theme**: Orange (#E67E22) & Blue (#2980B9)  
**Odoo Version**: 15.0 Community
