# -*- coding: utf-8 -*-

import logging
import requests
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GoogleCalendarIntegration(models.Model):
    _name = 'google.calendar.integration'
    _description = 'Tích hợp Google Calendar API'
    
    name = fields.Char(string='Tên', default='Google Calendar Integration')
    client_id = fields.Char(string='Client ID', required=True)
    client_secret = fields.Char(string='Client Secret')
    redirect_uri = fields.Char(string='Redirect URI', default='http://localhost:8069/google_calendar/callback', required=True, help='URI để Google redirect sau khi user authorize. PHẢI GIỐNG với Google Console 100%')
    access_token = fields.Text(string='Access Token')
    refresh_token = fields.Text(string='Refresh Token', help='Được tự động lưu sau khi user authorize qua OAuth flow')
    token_expiry = fields.Datetime(string='Token Expiry')
    calendar_id = fields.Char(string='Calendar ID', default='primary', help='ID của calendar, mặc định là "primary"')
    is_active = fields.Boolean(string='Kích hoạt', default=True)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.is_active:
            (self.search([('id', '!=', record.id), ('is_active', '=', True)])).write({'is_active': False})
        return record

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_active'):
            for rec in self.filtered('is_active'):
                (self.search([('id', '!=', rec.id), ('is_active', '=', True)])).write({'is_active': False})
        return res
    
    def get_authorization_url(self):
        """Tạo URL để user authorize Google Calendar"""
        self.ensure_one()
        
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'https://www.googleapis.com/auth/calendar',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        from urllib.parse import urlencode
        return f"{base_url}?{urlencode(params)}"
    
    def action_open_authorization_url(self):
        """Action để mở URL authorize trong browser"""
        self.ensure_one()
        
        auth_url = self.get_authorization_url()
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }
    
    def _refresh_access_token(self):
        """Làm mới access token từ refresh token"""
        self.ensure_one()
        
        # Kiểm tra có refresh_token chưa
        if not self.refresh_token:
            auth_url = self.get_authorization_url()
            raise UserError(_(
                "Chưa có Refresh Token!\n\n"
                "Vui lòng authorize Google Calendar trước:\n"
                "1. Truy cập URL sau (hoặc bấm nút 'Authorize Google' trên form):\n%s\n\n"
                "2. Đăng nhập Google và cho phép truy cập\n"
                "3. Google sẽ redirect về Odoo và tự động lưu tokens"
            ) % auth_url)
        
        # Kiểm tra token còn hạn không
        if self.access_token and self.token_expiry:
            if fields.Datetime.now() < self.token_expiry:
                return self.access_token
        
        # Làm mới token
        url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            result = response.json()

            # Nếu Google trả lỗi, log chi tiết và báo lỗi rõ ràng
            if response.status_code >= 400 or 'error' in result:
                _logger.error("Làm mới token Google thất bại: status=%s, body=%s", response.status_code, result)
                raise UserError(_("Không thể kết nối Google API: %s") % result)

            access_token = result.get('access_token')
            expires_in = result.get('expires_in', 3600)
            
            # Lưu token mới
            self.write({
                'access_token': access_token,
                'token_expiry': fields.Datetime.now() + timedelta(seconds=expires_in - 60)
            })
            
            return access_token
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi làm mới Google access token: {str(e)}")
            raise UserError(_("Không thể kết nối với Google API: %s") % str(e))
    
    def create_event(self, summary, start_datetime, end_datetime, description=None, 
                     location=None, attendees=None, meeting_link=None):
        """Tạo sự kiện trên Google Calendar"""
        self.ensure_one()
        
        access_token = self._refresh_access_token()
        
        calendar_id = self.calendar_id or 'primary'
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Chuyển đổi datetime sang timezone Asia/Ho_Chi_Minh
        # Odoo lưu datetime dạng UTC, cần convert sang local timezone
        import pytz
        local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        
        if isinstance(start_datetime, datetime):
            # Datetime từ Odoo là UTC naive, cần localize và convert
            if not start_datetime.tzinfo:
                start_datetime = pytz.UTC.localize(start_datetime)
            start_datetime_local = start_datetime.astimezone(local_tz)
            start_str = start_datetime_local.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            start_str = start_datetime
            
        if isinstance(end_datetime, datetime):
            if not end_datetime.tzinfo:
                end_datetime = pytz.UTC.localize(end_datetime)
            end_datetime_local = end_datetime.astimezone(local_tz)
            end_str = end_datetime_local.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            end_str = end_datetime
        
        event_data = {
            'summary': summary,
            'start': {
                'dateTime': start_str,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'end': {
                'dateTime': end_str,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 ngày trước
                    {'method': 'popup', 'minutes': 30},  # 30 phút trước
                ],
            },
        }
        
        if description:
            # Thêm link họp Zoom vào mô tả nếu có
            if meeting_link:
                description = f"{description}\n\n🔗 Link họp Zoom: {meeting_link}"
            event_data['description'] = description
        elif meeting_link:
            event_data['description'] = f"🔗 Link họp Zoom: {meeting_link}"
        
        if location:
            event_data['location'] = location
        
        if attendees:
            event_data['attendees'] = [{'email': email} for email in attendees if email]
            event_data['sendUpdates'] = 'all'  # Gửi email mời cho tất cả
        
        try:
            response = requests.post(url, headers=headers, json=event_data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': True,
                'event_id': result.get('id'),
                'html_link': result.get('htmlLink'),
                'ical_uid': result.get('iCalUID'),
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi tạo Google Calendar event: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                _logger.error(f"Response: {e.response.text}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_event(self, event_id, summary=None, start_datetime=None, end_datetime=None, 
                     description=None, location=None, attendees=None):
        """Cập nhật sự kiện trên Google Calendar"""
        self.ensure_one()
        
        access_token = self._refresh_access_token()
        
        calendar_id = self.calendar_id or 'primary'
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Lấy event hiện tại
        try:
            get_response = requests.get(url, headers=headers, timeout=30)
            get_response.raise_for_status()
            event_data = get_response.json()
        except:
            return {'success': False, 'error': 'Không tìm thấy sự kiện'}
        
        import pytz
        local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        
        if summary:
            event_data['summary'] = summary
        if start_datetime:
            if isinstance(start_datetime, datetime):
                if not start_datetime.tzinfo:
                    start_datetime = pytz.UTC.localize(start_datetime)
                start_datetime_local = start_datetime.astimezone(local_tz)
                event_data['start'] = {
                    'dateTime': start_datetime_local.strftime('%Y-%m-%dT%H:%M:%S'),
                    'timeZone': 'Asia/Ho_Chi_Minh'
                }
            else:
                event_data['start'] = {'dateTime': start_datetime, 'timeZone': 'Asia/Ho_Chi_Minh'}
        if end_datetime:
            if isinstance(end_datetime, datetime):
                if not end_datetime.tzinfo:
                    end_datetime = pytz.UTC.localize(end_datetime)
                end_datetime_local = end_datetime.astimezone(local_tz)
                event_data['end'] = {
                    'dateTime': end_datetime_local.strftime('%Y-%m-%dT%H:%M:%S'),
                    'timeZone': 'Asia/Ho_Chi_Minh'
                }
            else:
                event_data['end'] = {'dateTime': end_datetime, 'timeZone': 'Asia/Ho_Chi_Minh'}
        if description:
            event_data['description'] = description
        if location:
            event_data['location'] = location
        if attendees:
            event_data['attendees'] = [{'email': email} for email in attendees if email]
        
        try:
            response = requests.put(url, headers=headers, json=event_data, timeout=30)
            response.raise_for_status()
            return {'success': True}
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi cập nhật Google Calendar event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_event(self, event_id):
        """Xóa sự kiện trên Google Calendar"""
        self.ensure_one()
        
        access_token = self._refresh_access_token()
        
        calendar_id = self.calendar_id or 'primary'
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            return {'success': True}
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi xóa Google Calendar event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @api.model
    def get_active_integration(self):
        """Lấy cấu hình Google Calendar đang hoạt động"""
        integration = self.search([('is_active', '=', True)], limit=1)
        if not integration:
            raise UserError(_("Chưa cấu hình tích hợp Google Calendar. Vui lòng vào Cấu hình > Google Calendar để thiết lập."))
        return integration
