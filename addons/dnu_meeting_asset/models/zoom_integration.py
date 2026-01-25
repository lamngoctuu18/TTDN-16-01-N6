# -*- coding: utf-8 -*-

import logging
import requests
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ZoomIntegration(models.Model):
    _name = 'zoom.integration'
    _description = 'Tích hợp Zoom API'
    
    name = fields.Char(string='Tên', default='Zoom Integration')
    account_id = fields.Char(string='Account ID', required=True)
    client_id = fields.Char(string='Client ID', required=True)
    client_secret = fields.Char(string='Client Secret', required=True)
    access_token = fields.Text(string='Access Token')
    token_expiry = fields.Datetime(string='Token Expiry')
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
    
    def _get_access_token(self):
        """Lấy access token từ Zoom Server-to-Server OAuth"""
        self.ensure_one()
        
        # Kiểm tra token còn hạn không
        if self.access_token and self.token_expiry:
            if fields.Datetime.now() < self.token_expiry:
                return self.access_token
        
        # Lấy token mới
        url = "https://zoom.us/oauth/token"
        
        auth = (self.client_id, self.client_secret)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'account_credentials',
            'account_id': self.account_id
        }
        
        try:
            response = requests.post(url, auth=auth, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            access_token = result.get('access_token')
            expires_in = result.get('expires_in', 3600)
            
            # Lưu token
            self.write({
                'access_token': access_token,
                'token_expiry': fields.Datetime.now() + timedelta(seconds=expires_in - 60)
            })
            
            return access_token
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi lấy Zoom access token: {str(e)}")
            raise UserError(_("Không thể kết nối với Zoom API: %s") % str(e))
    
    def create_meeting(self, topic, start_time, duration_minutes, description=None, attendees=None):
        """Tạo cuộc họp Zoom"""
        self.ensure_one()
        
        access_token = self._get_access_token()
        
        url = "https://api.zoom.us/v2/users/me/meetings"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Chuyển đổi thời gian sang ISO format
        if isinstance(start_time, datetime):
            start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            start_time_str = start_time
        
        meeting_data = {
            'topic': topic,
            'type': 2,  # Scheduled meeting
            'start_time': start_time_str,
            'duration': duration_minutes,
            'timezone': 'Asia/Ho_Chi_Minh',
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': True,
                'mute_upon_entry': True,
                'waiting_room': False,
                'audio': 'both',
                'auto_recording': 'none',
            }
        }
        
        if description:
            meeting_data['agenda'] = description
        
        try:
            response = requests.post(url, headers=headers, json=meeting_data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': True,
                'meeting_id': result.get('id'),
                'join_url': result.get('join_url'),
                'start_url': result.get('start_url'),
                'password': result.get('password'),
                'host_email': result.get('host_email'),
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi tạo Zoom meeting: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_meeting(self, meeting_id, topic=None, start_time=None, duration_minutes=None):
        """Cập nhật cuộc họp Zoom"""
        self.ensure_one()
        
        access_token = self._get_access_token()
        
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        meeting_data = {}
        if topic:
            meeting_data['topic'] = topic
        if start_time:
            if isinstance(start_time, datetime):
                meeting_data['start_time'] = start_time.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                meeting_data['start_time'] = start_time
        if duration_minutes:
            meeting_data['duration'] = duration_minutes
        
        try:
            response = requests.patch(url, headers=headers, json=meeting_data, timeout=30)
            response.raise_for_status()
            return {'success': True}
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi cập nhật Zoom meeting: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_meeting(self, meeting_id):
        """Xóa cuộc họp Zoom"""
        self.ensure_one()
        
        access_token = self._get_access_token()
        
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            return {'success': True}
        except requests.exceptions.RequestException as e:
            _logger.error(f"Lỗi khi xóa Zoom meeting: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @api.model
    def get_active_integration(self):
        """Lấy cấu hình Zoom đang hoạt động"""
        integration = self.search([('is_active', '=', True)], limit=1)
        if not integration:
            raise UserError(_("Chưa cấu hình tích hợp Zoom. Vui lòng vào Cấu hình > Zoom để thiết lập."))
        return integration
