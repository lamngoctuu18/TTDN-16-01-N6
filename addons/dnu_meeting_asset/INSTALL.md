# Hướng dẫn cài đặt nhanh

## Bước 1: Chuẩn bị

Đảm bảo đã cài đặt:
- Odoo 15
- Module HR (hr)
- Module Calendar (calendar)

## Bước 2: Cài đặt module

### Cách 1: Từ giao diện Odoo

1. Vào **Settings → Apps → Update Apps List**
2. Tìm "**DNU Meeting & Asset Management**"
3. Click **Install**

### Cách 2: Từ command line

```bash
cd /home/tulam18/Business-Internship
python odoo-bin -c odoo.conf -d your_database -i dnu_meeting_asset
```

## Bước 3: Cấu hình cơ bản

### 3.1. Tạo Users và gán quyền

```
Settings → Users & Companies → Users
```

Tạo/chỉnh sửa users với quyền:
- **Asset Manager**: Quản lý tài sản
- **Meeting Manager**: Quản lý phòng họp  
- **Facility Staff**: Quyền đầy đủ

### 3.2. Tạo dữ liệu cơ bản

#### Danh mục tài sản:
```
Asset & Meeting → Quản lý tài sản → Danh mục → Create
- Thiết bị IT
- Thiết bị điện tử
- Đồ nội thất
```

#### Phòng họp:
```
Asset & Meeting → Quản lý phòng họp → Phòng họp → Create
- Phòng họp A (10 người)
- Phòng họp B (20 người)
- Phòng hội nghị (50 người)
```

## Bước 4: Demo & Test

### Tạo tài sản demo
```
Asset & Meeting → Quản lý tài sản → Tài sản → Create
- Tên: Máy chiếu Epson
- Danh mục: Thiết bị điện tử
- Giá: 15,000,000 VNĐ
```

### Đặt phòng demo
```
Asset & Meeting → Quản lý phòng họp → Đặt phòng
- Calendar view → Click vào ngày mai
- Chọn phòng, nhập chủ đề
- Click "Xác nhận"
```

## Bước 5: Kiểm tra Email

### Cấu hình SMTP (tùy chọn)
```
Settings → Technical → Email → Outgoing Mail Servers
```

Cấu hình để gửi email xác nhận/nhắc nhở booking.

## Bước 6: API Testing (tùy chọn)

### Kiểm tra API
```python
import requests
import json

url = 'http://localhost:8069/api/meeting/rooms'
headers = {'Content-Type': 'application/json'}
data = {
    "jsonrpc": "2.0",
    "params": {}
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.json())
```

## Xử lý sự cố

### Lỗi cài đặt
```bash
# Kiểm tra log
tail -f /var/log/odoo/odoo-server.log

# Cập nhật module
python odoo-bin -c odoo.conf -d your_database -u dnu_meeting_asset
```

### Lỗi quyền truy cập
```
Settings → Users → [User] → Access Rights
Kiểm tra và gán nhóm: Asset Manager / Meeting Manager
```

## Hoàn tất!

Module đã sẵn sàng sử dụng. Tham khảo file **README.md** để biết thêm chi tiết.

---

**Liên hệ hỗ trợ:**
- GitHub: [Link repo]
- Email: [Email support]
