# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import json


class MeetingAssetAPI(http.Controller):
    """
    REST API cho Meeting & Asset Management
    Endpoints cho mobile app và external integrations
    """

    # ==================== MEETING ROOM APIs ====================
    
    @http.route('/api/meeting/rooms', type='json', auth='user', methods=['GET'], csrf=False)
    def get_rooms(self, **kwargs):
        """
        Lấy danh sách phòng họp
        Query params: state, capacity_min, location
        """
        try:
            domain = []
            
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))
            if kwargs.get('capacity_min'):
                domain.append(('capacity', '>=', int(kwargs['capacity_min'])))
            if kwargs.get('location'):
                domain.append(('location', 'ilike', kwargs['location']))
            
            rooms = request.env['dnu.meeting.room'].search(domain)
            
            result = []
            for room in rooms:
                result.append({
                    'id': room.id,
                    'name': room.name,
                    'code': room.code,
                    'capacity': room.capacity,
                    'location': room.location,
                    'state': room.state,
                    'is_available_now': room.is_available_now,
                    'has_projector': room.has_projector,
                    'has_tv': room.has_tv,
                    'has_whiteboard': room.has_whiteboard,
                    'has_video_conference': room.has_video_conference,
                })
            
            return {
                'success': True,
                'data': result,
                'count': len(result)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/rooms/<int:room_id>/availability', type='json', auth='user', methods=['GET'], csrf=False)
    def check_room_availability(self, room_id, start_datetime, end_datetime, **kwargs):
        """
        Kiểm tra tình trạng phòng trong khoảng thời gian
        Params:
            - start_datetime: ISO format string
            - end_datetime: ISO format string
        """
        try:
            room = request.env['dnu.meeting.room'].browse(room_id)
            if not room.exists():
                return {
                    'success': False,
                    'error': 'Room not found'
                }
            
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            available, conflicts = room.check_availability(start_dt, end_dt)
            
            conflict_list = []
            for conflict in conflicts:
                conflict_list.append({
                    'id': conflict.id,
                    'name': conflict.name,
                    'subject': conflict.subject,
                    'start': conflict.start_datetime.isoformat(),
                    'end': conflict.end_datetime.isoformat(),
                    'organizer': conflict.organizer_id.name,
                })
            
            return {
                'success': True,
                'data': {
                    'available': available,
                    'room_name': room.name,
                    'conflicts': conflict_list
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/rooms/<int:room_id>/slots', type='json', auth='user', methods=['GET'], csrf=False)
    def get_available_slots(self, room_id, date, duration_hours=1.0, **kwargs):
        """
        Lấy các khung giờ còn trống của phòng trong ngày
        Params:
            - date: YYYY-MM-DD
            - duration_hours: float (default 1.0)
        """
        try:
            room = request.env['dnu.meeting.room'].browse(room_id)
            if not room.exists():
                return {
                    'success': False,
                    'error': 'Room not found'
                }
            
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            slots = room.get_available_slots(date_obj, float(duration_hours))
            
            slots_data = []
            for start, end in slots:
                slots_data.append({
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                })
            
            return {
                'success': True,
                'data': {
                    'room_name': room.name,
                    'date': date,
                    'slots': slots_data
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== BOOKING APIs ====================
    
    @http.route('/api/meeting/bookings', type='json', auth='user', methods=['POST'], csrf=False)
    def create_booking(self, **kwargs):
        """
        Tạo booking mới
        Required params:
            - room_id
            - subject
            - start_datetime (ISO format)
            - end_datetime (ISO format)
        Optional:
            - attendee_ids: list of employee IDs
            - description
            - num_external_attendees
        """
        try:
            # Validation
            required_fields = ['room_id', 'subject', 'start_datetime', 'end_datetime']
            for field in required_fields:
                if field not in kwargs:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Parse datetime
            start_dt = datetime.fromisoformat(kwargs['start_datetime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(kwargs['end_datetime'].replace('Z', '+00:00'))
            
            # Get organizer (current user's employee)
            organizer = request.env.user.employee_id
            if not organizer:
                return {
                    'success': False,
                    'error': 'Current user is not linked to an employee'
                }
            
            # Create booking
            vals = {
                'room_id': int(kwargs['room_id']),
                'subject': kwargs['subject'],
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'organizer_id': organizer.id,
                'description': kwargs.get('description', ''),
                'external_attendees': int(kwargs.get('num_external_attendees', 0)),
            }
            
            if kwargs.get('attendee_ids'):
                vals['attendee_ids'] = [(6, 0, kwargs['attendee_ids'])]
            
            booking = request.env['dnu.meeting.booking'].create(vals)
            
            # Auto confirm if user has permission
            if request.env.user.has_group('dnu_meeting_asset.group_meeting_manager'):
                booking.action_confirm()
            else:
                booking.action_submit()
            
            return {
                'success': True,
                'data': {
                    'id': booking.id,
                    'name': booking.name,
                    'state': booking.state,
                    'message': 'Booking created successfully'
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/bookings/<int:booking_id>', type='json', auth='user', methods=['GET'], csrf=False)
    def get_booking(self, booking_id, **kwargs):
        """Lấy thông tin chi tiết booking"""
        try:
            booking = request.env['dnu.meeting.booking'].browse(booking_id)
            if not booking.exists():
                return {
                    'success': False,
                    'error': 'Booking not found'
                }
            
            return {
                'success': True,
                'data': {
                    'id': booking.id,
                    'name': booking.name,
                    'subject': booking.subject,
                    'room': {
                        'id': booking.room_id.id,
                        'name': booking.room_id.name,
                        'location': booking.room_id.location,
                    },
                    'organizer': {
                        'id': booking.organizer_id.id,
                        'name': booking.organizer_id.name,
                    },
                    'start_datetime': booking.start_datetime.isoformat(),
                    'end_datetime': booking.end_datetime.isoformat(),
                    'duration': booking.duration,
                    'num_attendees': booking.num_attendees,
                    'state': booking.state,
                    'description': booking.description or '',
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/bookings/<int:booking_id>/checkin', type='json', auth='user', methods=['POST'], csrf=False)
    def checkin_booking(self, booking_id, **kwargs):
        """Check-in vào phòng"""
        try:
            booking = request.env['dnu.meeting.booking'].browse(booking_id)
            if not booking.exists():
                return {
                    'success': False,
                    'error': 'Booking not found'
                }
            
            booking.action_checkin()
            
            return {
                'success': True,
                'message': 'Checked in successfully',
                'data': {
                    'checkin_datetime': booking.checkin_datetime.isoformat(),
                    'checkin_by': booking.checkin_by.name,
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/bookings/<int:booking_id>/checkout', type='json', auth='user', methods=['POST'], csrf=False)
    def checkout_booking(self, booking_id, **kwargs):
        """Check-out khỏi phòng"""
        try:
            booking = request.env['dnu.meeting.booking'].browse(booking_id)
            if not booking.exists():
                return {
                    'success': False,
                    'error': 'Booking not found'
                }
            
            booking.action_checkout()
            
            return {
                'success': True,
                'message': 'Checked out successfully',
                'data': {
                    'checkout_datetime': booking.checkout_datetime.isoformat(),
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/bookings/<int:booking_id>/cancel', type='json', auth='user', methods=['POST'], csrf=False)
    def cancel_booking(self, booking_id, reason='', **kwargs):
        """Hủy booking"""
        try:
            booking = request.env['dnu.meeting.booking'].browse(booking_id)
            if not booking.exists():
                return {
                    'success': False,
                    'error': 'Booking not found'
                }
            
            booking.cancellation_reason = reason
            booking.action_cancel()
            
            return {
                'success': True,
                'message': 'Booking cancelled successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/meeting/my-bookings', type='json', auth='user', methods=['GET'], csrf=False)
    def get_my_bookings(self, **kwargs):
        """Lấy danh sách booking của user hiện tại"""
        try:
            organizer = request.env.user.employee_id
            if not organizer:
                return {
                    'success': False,
                    'error': 'Current user is not linked to an employee'
                }
            
            domain = [('organizer_id', '=', organizer.id)]
            
            # Filter by state
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))
            
            # Filter by date range
            if kwargs.get('date_from'):
                domain.append(('start_datetime', '>=', kwargs['date_from']))
            if kwargs.get('date_to'):
                domain.append(('end_datetime', '<=', kwargs['date_to']))
            
            bookings = request.env['dnu.meeting.booking'].search(domain, order='start_datetime desc')
            
            result = []
            for booking in bookings:
                result.append({
                    'id': booking.id,
                    'name': booking.name,
                    'subject': booking.subject,
                    'room_name': booking.room_id.name,
                    'start_datetime': booking.start_datetime.isoformat(),
                    'end_datetime': booking.end_datetime.isoformat(),
                    'state': booking.state,
                    'can_checkin': booking.can_checkin,
                })
            
            return {
                'success': True,
                'data': result,
                'count': len(result)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== ASSET APIs ====================
    
    @http.route('/api/assets', type='json', auth='user', methods=['GET'], csrf=False)
    def get_assets(self, **kwargs):
        """Lấy danh sách tài sản"""
        try:
            domain = []
            
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))
            if kwargs.get('category_id'):
                domain.append(('category_id', '=', int(kwargs['category_id'])))
            if kwargs.get('assigned_to_me'):
                employee = request.env.user.employee_id
                if employee:
                    domain.append(('assigned_to', '=', employee.id))
            
            assets = request.env['dnu.asset'].search(domain)
            
            result = []
            for asset in assets:
                result.append({
                    'id': asset.id,
                    'code': asset.code,
                    'name': asset.name,
                    'category': asset.category_id.name,
                    'state': asset.state,
                    'assigned_to': asset.assigned_to.name if asset.assigned_to else None,
                    'location': asset.location,
                })
            
            return {
                'success': True,
                'data': result,
                'count': len(result)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/assets/<int:asset_id>', type='json', auth='user', methods=['GET'], csrf=False)
    def get_asset(self, asset_id, **kwargs):
        """Lấy thông tin chi tiết tài sản"""
        try:
            asset = request.env['dnu.asset'].browse(asset_id)
            if not asset.exists():
                return {
                    'success': False,
                    'error': 'Asset not found'
                }
            
            return {
                'success': True,
                'data': {
                    'id': asset.id,
                    'code': asset.code,
                    'name': asset.name,
                    'category': asset.category_id.name,
                    'serial_number': asset.serial_number,
                    'state': asset.state,
                    'assigned_to': asset.assigned_to.name if asset.assigned_to else None,
                    'location': asset.location,
                    'purchase_date': asset.purchase_date.isoformat() if asset.purchase_date else None,
                    'purchase_value': asset.purchase_value,
                    'current_value': asset.current_value,
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== ASSET LENDING APIs ====================
    
    @http.route('/api/assets/lending', type='json', auth='user', methods=['GET'], csrf=False)
    def get_lendings(self, **kwargs):
        """Lấy danh sách phiếu mượn tài sản"""
        try:
            domain = []
            
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))
            if kwargs.get('my_lendings'):
                employee = request.env.user.employee_id
                if employee:
                    domain.append(('borrower_id', '=', employee.id))
            
            lendings = request.env['dnu.asset.lending'].search(domain, order='date_borrow desc')
            
            result = []
            for lending in lendings:
                result.append({
                    'id': lending.id,
                    'name': lending.name,
                    'asset': {
                        'id': lending.asset_id.id,
                        'name': lending.asset_id.name,
                        'code': lending.asset_id.code,
                    },
                    'borrower': lending.borrower_id.name,
                    'date_borrow': lending.date_borrow.isoformat(),
                    'date_expected_return': lending.date_expected_return.isoformat(),
                    'state': lending.state,
                    'is_overdue': lending.is_overdue,
                })
            
            return {
                'success': True,
                'data': result,
                'count': len(result)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/assets/lending', type='json', auth='user', methods=['POST'], csrf=False)
    def create_lending(self, **kwargs):
        """Tạo yêu cầu mượn tài sản"""
        try:
            required_fields = ['asset_id', 'date_expected_return', 'purpose']
            for field in required_fields:
                if field not in kwargs:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            borrower = request.env.user.employee_id
            if not borrower:
                return {
                    'success': False,
                    'error': 'Current user is not linked to an employee'
                }
            
            vals = {
                'asset_id': int(kwargs['asset_id']),
                'borrower_id': borrower.id,
                'date_expected_return': datetime.fromisoformat(kwargs['date_expected_return'].replace('Z', '+00:00')),
                'purpose': kwargs['purpose'],
                'purpose_note': kwargs.get('purpose_note', ''),
                'location': kwargs.get('location', ''),
            }
            
            lending = request.env['dnu.asset.lending'].create(vals)
            lending.action_request()
            
            return {
                'success': True,
                'data': {
                    'id': lending.id,
                    'name': lending.name,
                    'state': lending.state,
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/assets/lending/<int:lending_id>/return', type='json', auth='user', methods=['POST'], csrf=False)
    def return_lending(self, lending_id, **kwargs):
        """Trả tài sản mượn"""
        try:
            lending = request.env['dnu.asset.lending'].browse(lending_id)
            if not lending.exists():
                return {
                    'success': False,
                    'error': 'Lending record not found'
                }
            
            lending.write({
                'return_condition': kwargs.get('return_condition', 'good'),
                'return_notes': kwargs.get('return_notes', ''),
            })
            
            lending.action_return()
            
            return {
                'success': True,
                'message': 'Asset returned successfully',
                'data': {
                    'date_actual_return': lending.date_actual_return.isoformat(),
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== DASHBOARD APIs ====================
    
    @http.route('/api/dashboard/summary', type='json', auth='user', methods=['GET'], csrf=False)
    def get_dashboard_summary(self, **kwargs):
        """Lấy thống kê tổng quan cho dashboard"""
        try:
            today = datetime.now().date()
            
            # Asset statistics
            Asset = request.env['dnu.asset']
            assets_total = Asset.search_count([])
            assets_available = Asset.search_count([('state', '=', 'available')])
            assets_assigned = Asset.search_count([('state', '=', 'assigned')])
            assets_maintenance = Asset.search_count([('state', '=', 'maintenance')])
            
            # Room statistics
            Room = request.env['dnu.meeting.room']
            rooms_total = Room.search_count([])
            rooms_available = Room.search_count([('state', '=', 'available'), ('is_available_now', '=', True)])
            
            # Booking statistics
            Booking = request.env['dnu.meeting.booking']
            bookings_today = Booking.search_count([
                ('start_datetime', '>=', today.strftime('%Y-%m-%d 00:00:00')),
                ('start_datetime', '<=', today.strftime('%Y-%m-%d 23:59:59')),
                ('state', 'in', ['confirmed', 'in_progress']),
            ])
            
            # Lending statistics
            Lending = request.env['dnu.asset.lending']
            lendings_active = Lending.search_count([('state', '=', 'borrowed')])
            lendings_overdue = Lending.search_count([('state', '=', 'overdue')])
            
            # Maintenance statistics
            Maintenance = request.env['dnu.asset.maintenance']
            maintenance_pending = Maintenance.search_count([('state', '=', 'pending')])
            
            return {
                'success': True,
                'data': {
                    'assets': {
                        'total': assets_total,
                        'available': assets_available,
                        'assigned': assets_assigned,
                        'maintenance': assets_maintenance,
                    },
                    'rooms': {
                        'total': rooms_total,
                        'available_now': rooms_available,
                    },
                    'bookings': {
                        'today': bookings_today,
                    },
                    'lendings': {
                        'active': lendings_active,
                        'overdue': lendings_overdue,
                    },
                    'maintenance': {
                        'pending': maintenance_pending,
                    },
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class GoogleCalendarOAuth(http.Controller):
    """OAuth callback handler for Google Calendar integration"""
    
    @http.route('/google_calendar/callback', type='http', auth='public', methods=['GET'], csrf=False)
    def google_calendar_callback(self, **kwargs):
        """
        Xử lý callback từ Google OAuth2
        Nhận authorization code và đổi lấy access_token + refresh_token
        """
        code = kwargs.get('code')
        error = kwargs.get('error')
        
        if error:
            return request.render('dnu_meeting_asset.google_auth_error', {
                'error': error,
                'error_description': kwargs.get('error_description', 'Unknown error')
            })
        
        if not code:
            return request.render('dnu_meeting_asset.google_auth_error', {
                'error': 'missing_code',
                'error_description': 'Authorization code not found'
            })
        
        try:
            # Lấy config Google Calendar
            GoogleCal = request.env['google.calendar.integration'].sudo()
            config = GoogleCal.search([('is_active', '=', True)], limit=1)
            
            if not config:
                return request.render('dnu_meeting_asset.google_auth_error', {
                    'error': 'no_config',
                    'error_description': 'Google Calendar integration not configured'
                })
            
            # Đổi authorization code lấy tokens
            import requests as req
            
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                'code': code,
                'client_id': config.client_id,
                'client_secret': config.client_secret,
                'redirect_uri': config.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = req.post(token_url, data=data, timeout=30)
            result = response.json()
            
            if response.status_code >= 400 or 'error' in result:
                return request.render('dnu_meeting_asset.google_auth_error', {
                    'error': result.get('error', 'token_exchange_failed'),
                    'error_description': result.get('error_description', str(result))
                })
            
            # Lưu tokens
            access_token = result.get('access_token')
            refresh_token = result.get('refresh_token')
            expires_in = result.get('expires_in', 3600)
            
            # CHỈ ghi đè refresh_token nếu có (Google chỉ trả về lần đầu)
            vals = {
                'access_token': access_token,
                'token_expiry': datetime.now() + timedelta(seconds=expires_in - 60)
            }
            
            if refresh_token:
                vals['refresh_token'] = refresh_token
            
            config.write(vals)
            
            return request.render('dnu_meeting_asset.google_auth_success', {
                'config_name': config.name
            })
            
        except Exception as e:
            return request.render('dnu_meeting_asset.google_auth_error', {
                'error': 'exception',
                'error_description': str(e)
            })
