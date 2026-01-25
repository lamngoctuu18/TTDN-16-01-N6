# Hướng Dẫn Cấu Hình DNU Meeting Asset

## ⚠️ Quan Trọng: Cấu Hình API Keys và Secrets

Module này yêu cầu cấu hình các API keys và secrets sau khi cài đặt. **KHÔNG BAO GIỜ** commit các thông tin nhạy cảm vào Git.

## 1. OpenAI API Configuration

### Cách 1: Qua giao diện Odoo (Khuyến nghị)
1. Vào **Settings** > **Technical** > **OpenAI Configuration**
2. Tạo hoặc chỉnh sửa cấu hình mặc định
3. Nhập API Key của bạn từ [OpenAI Platform](https://platform.openai.com/api-keys)
4. Chọn model (ví dụ: `gpt-4o-mini`)
5. Đặt `Active` = True

### Cách 2: Qua System Parameters
1. Vào **Settings** > **Technical** > **Parameters** > **System Parameters**
2. Tạo parameter mới:
   - Key: `openai.api_key`
   - Value: `sk-proj-YOUR_ACTUAL_KEY_HERE`

## 2. Zoom Integration Configuration

1. Vào **Settings** > **Zoom Integration**
2. Nhập thông tin từ [Zoom Marketplace](https://marketplace.zoom.us/):
   - Account ID
   - Client ID
   - Client Secret
3. Đặt `Active` = True

## 3. Google Calendar Integration Configuration

1. Tạo OAuth 2.0 credentials tại [Google Cloud Console](https://console.cloud.google.com/):
   - Vào **APIs & Services** > **Credentials**
   - Tạo **OAuth 2.0 Client ID**
   - Authorized redirect URI: `http://localhost:8069/google_calendar/callback`

2. Vào **Settings** > **Google Calendar Integration** trong Odoo
3. Nhập:
   - Client ID
   - Client Secret
   - Redirect URI
4. Đặt `Active` = True

## 4. Bảo Mật

### File .gitignore
Đảm bảo các file sau được thêm vào `.gitignore`:
```
# Odoo configs with secrets
odoo.conf
*.conf.local

# Data files with secrets
addons/*/data/*_credentials.xml
addons/*/data/*_secrets.xml

# Environment variables
.env
.env.local
```

### Biến Môi Trường (Tùy Chọn)
Bạn có thể sử dụng biến môi trường:
```bash
export OPENAI_API_KEY="sk-proj-YOUR_KEY"
export ZOOM_CLIENT_ID="YOUR_ZOOM_CLIENT"
export ZOOM_CLIENT_SECRET="YOUR_ZOOM_SECRET"
export GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT"
export GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_SECRET"
```

## 5. Khắc Phục Sự Cố

### Lỗi: "OpenAI API Key not configured"
- Kiểm tra đã cấu hình API key chưa
- Đảm bảo configuration có `Active` = True
- Restart Odoo server

### Lỗi: "Zoom authentication failed"
- Kiểm tra Zoom credentials
- Đảm bảo Zoom app đã được publish/activated

### Lỗi: "Google Calendar authorization failed"
- Kiểm tra redirect URI khớp với Google Cloud Console
- Authorize lại qua Settings > Google Calendar > Authorize

## 6. Production Deployment

Khi deploy lên production:
1. **KHÔNG** sử dụng data XML files với credentials
2. Sử dụng biến môi trường hoặc secret management service
3. Cấu hình qua Odoo UI sau khi cài đặt
4. Backup credentials an toàn
