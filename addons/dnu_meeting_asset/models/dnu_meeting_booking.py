# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class MeetingBooking(models.Model):
    _name = 'dnu.meeting.booking'
    _description = 'Đặt phòng họp'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(
        string='Mã đặt phòng',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    subject = fields.Char(
        string='Chủ đề cuộc họp',
        required=True,
        tracking=True,
        default='Cuộc họp'
    )
    room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng họp',
        required=True,
        tracking=True
    )
    
    # Time
    start_datetime = fields.Datetime(
        string='Thời gian bắt đầu',
        required=True,
        tracking=True,
        index=True
    )
    end_datetime = fields.Datetime(
        string='Thời gian kết thúc',
        required=True,
        tracking=True,
        index=True
    )
    duration = fields.Float(
        string='Thời lượng (giờ)',
        compute='_compute_duration',
        store=True
    )
    
    # Organizer & Attendees
    organizer_id = fields.Many2one(
        'hr.employee',
        string='Người tổ chức (HR)',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        help='Chọn người tổ chức từ hệ thống HR'
    )
    nhan_vien_to_chuc_id = fields.Many2one(
        'nhan_vien',
        string='Người tổ chức',
        tracking=True,
        help='Chọn người tổ chức từ hệ thống Nhân sự'
    )
    organizer_name = fields.Char(
        string='Tên người tổ chức',
        compute='_compute_organizer_name',
        store=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        related='organizer_id.department_id',
        store=True
    )
    
    @api.depends('organizer_id', 'nhan_vien_to_chuc_id')
    def _compute_organizer_name(self):
        for rec in self:
            if rec.nhan_vien_to_chuc_id:
                rec.organizer_name = rec.nhan_vien_to_chuc_id.ho_va_ten
            elif rec.organizer_id:
                rec.organizer_name = rec.organizer_id.name
            else:
                rec.organizer_name = False
    
    @api.onchange('nhan_vien_to_chuc_id')
    def _onchange_nhan_vien_to_chuc(self):
        """Tự động liên kết với HR employee nếu có"""
        if self.nhan_vien_to_chuc_id:
            # Tự động điền HR employee nếu có
            if self.nhan_vien_to_chuc_id.hr_employee_id:
                self.organizer_id = self.nhan_vien_to_chuc_id.hr_employee_id
    
    @api.onchange('organizer_id')
    def _onchange_organizer(self):
        """Tự động liên kết với nhân viên nếu có"""
        if self.organizer_id and self.organizer_id.nhan_vien_id:
            self.nhan_vien_to_chuc_id = self.organizer_id.nhan_vien_id
    
    @api.onchange('room_id')
    def _onchange_room_id(self):
        """Không tự động load thiết bị theo phòng"""
        return
    
    @api.onchange('num_attendees', 'need_projector', 'need_video_conference', 'need_whiteboard')
    def _onchange_num_attendees(self):
        """Đề xuất phòng họp phù hợp dựa trên số người tham dự"""
        if self.num_attendees > 0:
            # Tìm phòng có sức chứa >= số người và gần nhất
            domain = [
                ('capacity', '>=', self.num_attendees),
                ('state', '=', 'available'),
                ('allow_booking', '=', True),
            ]
            if self.need_projector:
                domain.append(('has_projector', '=', True))
            if self.need_video_conference:
                domain.append(('has_video_conference', '=', True))
            if self.need_whiteboard:
                domain.append(('has_whiteboard', '=', True))

            suitable_rooms = self.env['dnu.meeting.room'].search(domain, order='capacity asc', limit=5)
            
            if suitable_rooms:
                return {
                    'domain': {'room_id': [('id', 'in', suitable_rooms.ids)]}
                }
            else:
                return {
                    'warning': {
                        'title': 'Không tìm thấy phòng phù hợp',
                        'message': f'Không có phòng nào có sức chứa >= {self.num_attendees} người. Vui lòng giảm số lượng hoặc liên hệ quản lý.'
                    }
                }
    
    @api.depends('num_attendees', 'need_projector', 'need_video_conference', 'need_whiteboard')
    def _compute_suggested_rooms(self):
        """Tính toán danh sách phòng đề xuất"""
        for record in self:
            if record.num_attendees > 0:
                domain = [
                    ('capacity', '>=', record.num_attendees),
                    ('state', '=', 'available'),
                    ('allow_booking', '=', True),
                ]
                if record.need_projector:
                    domain.append(('has_projector', '=', True))
                if record.need_video_conference:
                    domain.append(('has_video_conference', '=', True))
                if record.need_whiteboard:
                    domain.append(('has_whiteboard', '=', True))

                suitable_rooms = self.env['dnu.meeting.room'].search(domain, order='capacity asc', limit=5)
                record.suggested_room_ids = suitable_rooms
            else:
                record.suggested_room_ids = False
    
    attendee_ids = fields.Many2many(
        'hr.employee',
        'booking_attendee_rel',
        'booking_id',
        'employee_id',
        string='Người tham dự'
    )
    num_attendees = fields.Integer(
        string='Số người tham dự',
        default=1,
        required=True,
        help='Tổng số người tham dự cuộc họp (bao gồm cả người tổ chức). Hệ thống sẽ tự động đề xuất phòng phù hợp.'
    )
    need_projector = fields.Boolean(string='Cần máy chiếu')
    need_video_conference = fields.Boolean(string='Cần hệ thống họp trực tuyến')
    need_whiteboard = fields.Boolean(string='Cần bảng trắng')
    suggested_room_ids = fields.Many2many(
        'dnu.meeting.room',
        'booking_suggested_room_rel',
        'booking_id',
        'room_id',
        string='Phòng đề xuất',
        compute='_compute_suggested_rooms',
        store=False,
        help='Danh sách phòng phù hợp với số người tham dự'
    )
    external_attendees = fields.Integer(
        string='Khách bên ngoài',
        default=0
    )
    
    # Equipment requests
    required_equipment_ids = fields.Many2many(
        'dnu.asset',
        'booking_equipment_rel',
        'booking_id',
        'asset_id',
        string='Bổ sung trang thiết bị',
        domain=[('state', 'in', ['available', 'assigned'])],
        help='Tài sản sẵn sàng hoặc đã gán có thể mượn. Tài sản đang được mượn sẽ bị chặn khi tạo phiếu.'
    )

    @api.onchange('start_datetime', 'end_datetime')
    def _onchange_booking_time_equipment_domain(self):
        """Chặn thiết bị đang được mượn trong khoảng thời gian đặt phòng"""
        domain = [('state', 'in', ['available', 'assigned'])]

        if self.start_datetime and self.end_datetime:
            active_lendings = self.env['dnu.asset.lending'].search([
                ('state', 'in', ['approved', 'borrowed']),
                ('date_borrow', '<', self.end_datetime),
                ('date_expected_return', '>', self.start_datetime),
            ])
            if active_lendings:
                domain.append(('id', 'not in', active_lendings.mapped('asset_id').ids))
        else:
            now = fields.Datetime.now()
            active_lendings = self.env['dnu.asset.lending'].search([
                ('state', 'in', ['approved', 'borrowed']),
                ('date_expected_return', '>=', now),
            ])
            if active_lendings:
                domain.append(('id', 'not in', active_lendings.mapped('asset_id').ids))

        return {'domain': {'required_equipment_ids': domain}}
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ duyệt'),
        ('confirmed', 'Đã xác nhận'),
        ('in_progress', 'Đang diễn ra'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # Check-in/out
    checkin_datetime = fields.Datetime(
        string='Thời gian check-in',
        readonly=True
    )
    checkout_datetime = fields.Datetime(
        string='Thời gian check-out',
        readonly=True
    )
    checkin_by = fields.Many2one(
        'res.users',
        string='Check-in bởi',
        readonly=True
    )
    
    # Additional info
    description = fields.Html(string='Mô tả cuộc họp')
    notes = fields.Text(string='Ghi chú')
    cancellation_reason = fields.Text(string='Lý do hủy')
    
    # Email tracking
    email_send_count = fields.Integer(
        string='Số lần gửi email',
        default=0,
        help='Số lần email thông báo đã được gửi cho booking này'
    )
    last_email_sent = fields.Datetime(
        string='Lần gửi email cuối',
        help='Thời điểm gửi email thông báo cuối cùng'
    )

    van_ban_den_count = fields.Integer(
        string='Văn bản đến',
        compute='_compute_van_ban_den_count',
        store=False
    )
    ai_request_count = fields.Integer(
        string='Số lượt hỏi AI',
        compute='_compute_ai_request_count',
        store=False
    )

    def _compute_van_ban_den_count(self):
        VanBanDen = self.env['van_ban_den']
        for rec in self:
            rec.van_ban_den_count = VanBanDen.search_count([
                ('source_model', '=', rec._name),
                ('source_res_id', '=', rec.id),
            ])

    def _compute_ai_request_count(self):
        Request = self.env['ai.request']
        for rec in self:
            rec.ai_request_count = Request.search_count([
                ('context_model', '=', rec._name),
                ('context_res_id', '=', rec.id),
            ])

    def action_view_van_ban_den(self):
        self.ensure_one()
        action = self.env.ref('quan_ly_van_ban.action_van_ban_den').read()[0]
        action['domain'] = [('source_model', '=', self._name), ('source_res_id', '=', self.id)]
        action['context'] = {
            'default_source_model': self._name,
            'default_source_res_id': self.id,
        }
        return action

    def action_view_ai_history(self):
        """Xem lịch sử hỏi AI của booking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử hỏi AI',
            'res_model': 'ai.request',
            'view_mode': 'tree,form',
            'domain': [
                ('context_model', '=', self._name),
                ('context_res_id', '=', self.id),
            ],
            'context': {
                'default_context_model': self._name,
                'default_context_res_id': self.id,
                'default_channel': 'meeting',
            },
        }

    def action_create_van_ban_den(self):
        self.ensure_one()
        handler_employee = self.nhan_vien_to_chuc_id or (self.organizer_id.nhan_vien_id if self.organizer_id and hasattr(self.organizer_id, 'nhan_vien_id') else False)
        department = handler_employee.don_vi_chinh_id if handler_employee else False
        due_date = fields.Date.to_string(self.start_datetime.date()) if self.start_datetime else False
        ten_van_ban = f'Văn bản đến - Đặt phòng {self.name}'
        if self.subject:
            ten_van_ban = f'Văn bản đến - {self.subject} ({self.name})'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo văn bản đến',
            'res_model': 'van_ban_den',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_source_model': self._name,
                'default_source_res_id': self.id,
                'default_ten_van_ban': ten_van_ban,
                'default_handler_employee_id': handler_employee.id if handler_employee else False,
                'default_department_id': department.id if department else False,
                'default_due_date': due_date,
            },
        }
    
    # Meeting type (Online/Offline)
    meeting_type = fields.Selection([
        ('offline', 'Trực tiếp (Offline)'),
        ('online', 'Trực tuyến (Zoom)'),
    ], string='Hình thức họp', default='offline', required=True, tracking=True)
    
    # Zoom integration fields
    zoom_meeting_id = fields.Char(string='Zoom Meeting ID', readonly=True, copy=False)
    zoom_join_url = fields.Char(string='Link tham gia Zoom', readonly=True, copy=False)
    zoom_start_url = fields.Char(string='Link bắt đầu Zoom (Host)', readonly=True, copy=False)
    zoom_password = fields.Char(string='Mật khẩu Zoom', readonly=True, copy=False)
    
    # Google Calendar integration fields
    google_calendar_event_id = fields.Char(string='Google Calendar Event ID', readonly=True, copy=False)
    google_calendar_link = fields.Char(string='Link Google Calendar', readonly=True, copy=False)

    # Event + Jitsi (event_meeting_room_extended) integration
    event_event_id = fields.Many2one(
        'event.event',
        string='Sự kiện (Event)',
        readonly=True,
        copy=False,
        ondelete='set null',
        help='Sự kiện được tạo từ booking (để dùng cộng đồng/phòng Jitsi).'
    )
    event_meeting_room_id = fields.Many2one(
        'event.meeting.room',
        string='Phòng Jitsi',
        readonly=True,
        copy=False,
        ondelete='set null',
        help='Phòng họp Jitsi (community room) được tạo từ booking.'
    )
    event_meeting_room_url = fields.Char(related='event_meeting_room_id.room_url', string='Link Jitsi', readonly=True)
    event_meeting_room_website_url = fields.Char(related='event_meeting_room_id.website_url', string='Link Community', readonly=True)
    
    # Integration status
    zoom_sync_status = fields.Selection([
        ('not_synced', 'Chưa đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('error', 'Lỗi'),
    ], string='Trạng thái Zoom', default='not_synced', readonly=True)
    google_sync_status = fields.Selection([
        ('not_synced', 'Chưa đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('error', 'Lỗi'),
    ], string='Trạng thái Google Calendar', default='not_synced', readonly=True)
    
    # Email tracking fields
    reminder_email_sent = fields.Boolean(
        string='Email nhắc đã gửi',
        default=False,
        help='Đánh dấu email nhắc lịch họp đã được gửi'
    )
    confirmation_email_sent = fields.Boolean(
        string='Email xác nhận đã gửi',
        default=False,
        help='Đánh dấu email xác nhận đã được gửi'
    )
    
    # Calendar integration
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Sự kiện lịch',
        ondelete='set null'
    )
    
    # Computed
    is_past = fields.Boolean(
        compute='_compute_is_past',
        string='Đã qua'
    )
    can_checkin = fields.Boolean(
        compute='_compute_can_checkin',
        string='Có thể check-in'
    )
    conflict_ids = fields.Many2many(
        'dnu.meeting.booking',
        compute='_compute_conflicts',
        string='Xung đột'
    )
    has_conflicts = fields.Boolean(
        compute='_compute_conflicts',
        string='Có xung đột'
    )
    
    # Lending records
    lending_ids = fields.One2many(
        'dnu.asset.lending',
        'booking_id',
        string='Phiếu mượn tài sản',
        help='Các phiếu mượn tài sản tự động được tạo từ booking này'
    )
    lending_count = fields.Integer(
        string='Số phiếu mượn',
        compute='_compute_lending_count',
        store=True
    )
    all_lendings_approved = fields.Boolean(
        string='Tất cả đã được duyệt',
        compute='_compute_lending_status',
        help='Tất cả phiếu mượn đã được ký duyệt'
    )
    has_pending_lendings = fields.Boolean(
        string='Có phiếu chờ duyệt',
        compute='_compute_lending_status',
        help='Có phiếu mượn đang chờ ký duyệt'
    )
    
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.meeting.booking') or _('New')
        
        booking = super(MeetingBooking, self).create(vals)

        # If created from calendar (or other UI) with auto-submit flag, push to 'submitted'
        # so it appears immediately in the approval list.
        if self.env.context.get('auto_submit_on_create') and booking.state == 'draft':
            booking.action_submit()
        
        # Tự động tạo calendar event nếu cần
        if booking.state == 'confirmed':
            booking._create_calendar_event()
            booking._send_confirmation_email()
            booking._send_notification_emails()
        else:
            booking._send_created_notification_email()
        
        return booking

    def write(self, vals):
        # Lưu giá trị cũ để so sánh
        old_values = {}
        important_fields = ['start_datetime', 'end_datetime', 'subject', 'room_id', 'zoom_join_url', 'google_calendar_link']
        
        for booking in self:
            if booking.state != 'cancelled' and any(key in vals for key in important_fields):
                old_values[booking.id] = {
                    'start_datetime': booking.start_datetime,
                    'end_datetime': booking.end_datetime,
                    'subject': booking.subject,
                    'room_id': booking.room_id.name,
                }
        
        result = super(MeetingBooking, self).write(vals)
        
        # Cập nhật calendar event
        if any(key in vals for key in ['start_datetime', 'end_datetime', 'subject', 'room_id']):
            for booking in self:
                if booking.calendar_event_id:
                    booking._update_calendar_event()

        # Đồng bộ Event/Jitsi room nếu booking đã tạo event
        if any(key in vals for key in ['start_datetime', 'end_datetime', 'subject']):
            for booking in self:
                if booking.event_event_id:
                    booking.event_event_id.sudo().write({
                        'name': booking.subject or booking.name,
                        'date_begin': booking.start_datetime,
                        'date_end': booking.end_datetime,
                    })
                if booking.event_meeting_room_id and 'subject' in vals:
                    booking.event_meeting_room_id.sudo().write({
                        'name': booking.subject or booking.name,
                    })
        
        # Gửi email thông báo nếu có thay đổi quan trọng
        if old_values and any(key in vals for key in important_fields):
            for booking in self:
                if booking.id in old_values:
                    booking._send_update_notification_email()
        
        return result

    def _get_or_create_event_type_for_community(self):
        """Pick an event.type configured for community rooms; create a default one if missing."""
        event_type = self.env['event.type'].search([('allow_community', '=', True)], limit=1)
        if event_type:
            return event_type

        return self.env['event.type'].sudo().create({
            'name': 'Phòng họp sự kiện (Community)',
            'allow_community': True,
            'allow_room_creation': True,
            'auto_room_creation': False,
            'default_room_capacity': 50,
        })

    def action_create_event_jitsi_room(self):
        """Create an Event + Jitsi community room from this booking."""
        self.ensure_one()

        if not self.start_datetime or not self.end_datetime:
            raise UserError(_('Vui lòng chọn thời gian bắt đầu/kết thúc trước khi tạo sự kiện.'))

        if self.state == 'cancelled':
            raise UserError(_('Không thể tạo sự kiện cho booking đã hủy.'))

        # Idempotent: if already created, just open the room
        if self.event_meeting_room_id:
            return self.action_open_event_meeting_room()

        # Ensure external integrations exist if user expects them
        # - Zoom: only when meeting_type is online
        if self.meeting_type == 'online' and not self.zoom_meeting_id:
            self.action_create_zoom_meeting()
        # - Google Calendar: create if not yet synced
        if not self.google_calendar_event_id:
            self.action_sync_google_calendar()

        event_type = self._get_or_create_event_type_for_community()

        event_vals = {
            'name': self.subject or self.name,
            'date_begin': self.start_datetime,
            'date_end': self.end_datetime,
            'event_type_id': event_type.id,
            'user_id': (self.create_uid.id if self.create_uid else self.env.user.id),
        }
        event = self.env['event.event'].sudo().create(event_vals)

        # Build a small HTML description referencing existing links
        html_lines = []
        html_lines.append('<p><b>Booking:</b> %s</p>' % (self.name or ''))
        if self.room_id:
            html_lines.append('<p><b>Phòng họp (offline):</b> %s</p>' % (self.room_id.display_name or ''))
        if self.organizer_name:
            html_lines.append('<p><b>Người tổ chức:</b> %s</p>' % (self.organizer_name or ''))
        if self.zoom_join_url:
            html_lines.append('<p><b>Zoom:</b> <a target="_blank" href="%s">%s</a></p>' % (self.zoom_join_url, self.zoom_join_url))
        if self.google_calendar_link:
            html_lines.append('<p><b>Google Calendar:</b> <a target="_blank" href="%s">%s</a></p>' % (self.google_calendar_link, self.google_calendar_link))

        room_capacity = max(int(self.num_attendees or 0), int(getattr(event_type, 'default_room_capacity', 50) or 50))
        room = self.env['event.meeting.room'].sudo().create({
            'name': self.subject or self.name,
            'summary': self.subject or self.name,
            'description': ''.join(html_lines) if html_lines else False,
            'event_id': event.id,
            'max_capacity': room_capacity,
            'website_published': True,
        })

        self.sudo().write({
            'event_event_id': event.id,
            'event_meeting_room_id': room.id,
        })

        return {
            'name': _('Phòng Jitsi'),
            'type': 'ir.actions.act_window',
            'res_model': 'event.meeting.room',
            'res_id': room.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_event_meeting_room(self):
        self.ensure_one()
        if not self.event_meeting_room_id:
            raise UserError(_('Booking này chưa có phòng Jitsi.'))

        url = self.event_meeting_room_website_url or self.event_meeting_room_url
        if not url:
            raise UserError(_('Không tìm thấy URL phòng Jitsi.'))

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for booking in self:
            if booking.start_datetime and booking.end_datetime:
                delta = booking.end_datetime - booking.start_datetime
                booking.duration = delta.total_seconds() / 3600.0
            else:
                booking.duration = 0.0

    @api.depends('end_datetime')
    def _compute_is_past(self):
        now = fields.Datetime.now()
        for booking in self:
            booking.is_past = booking.end_datetime < now if booking.end_datetime else False

    @api.depends('state', 'start_datetime', 'checkin_datetime')
    def _compute_can_checkin(self):
        now = fields.Datetime.now()
        for booking in self:
            # Có thể check-in 15 phút trước giờ họp
            can_checkin = (
                booking.state == 'confirmed' and
                not booking.checkin_datetime and
                booking.start_datetime and
                (booking.start_datetime - timedelta(minutes=15)) <= now <= booking.end_datetime
            )
            booking.can_checkin = can_checkin
    
    @api.depends('lending_ids')
    def _compute_lending_count(self):
        for booking in self:
            booking.lending_count = len(booking.lending_ids)
    
    @api.depends('lending_ids', 'lending_ids.state', 'lending_ids.approval_status')
    def _compute_lending_status(self):
        for booking in self:
            if not booking.lending_ids:
                booking.all_lendings_approved = True
                booking.has_pending_lendings = False
            else:
                # Kiểm tra có phiếu nào chưa được phê duyệt
                pending_lendings = booking.lending_ids.filtered(
                    lambda l: l.state == 'pending_approval' or l.approval_status == 'pending'
                )
                booking.has_pending_lendings = bool(pending_lendings)
                
                # Kiểm tra tất cả đã được phê duyệt chưa
                approved_lendings = booking.lending_ids.filtered(
                    lambda l: l.approval_status == 'approved' or l.state in ['approved', 'borrowed', 'returned']
                )
                booking.all_lendings_approved = (len(approved_lendings) == len(booking.lending_ids))

    @api.depends('room_id', 'start_datetime', 'end_datetime', 'state')
    def _compute_conflicts(self):
        for booking in self:
            if not booking.room_id or not booking.start_datetime or not booking.end_datetime:
                booking.conflict_ids = False
                booking.has_conflicts = False
                continue
            
            if booking.state == 'cancelled':
                booking.conflict_ids = False
                booking.has_conflicts = False
                continue
            
            # Skip conflict check for new records (not yet saved)
            if not booking.id or isinstance(booking.id, models.NewId):
                booking.conflict_ids = False
                booking.has_conflicts = False
                continue
            
            domain = [
                ('id', '!=', booking.id),
                ('room_id', '=', booking.room_id.id),
                ('state', '=', 'confirmed'),
                ('start_datetime', '<', booking.end_datetime),
                ('end_datetime', '>', booking.start_datetime),
            ]
            
            conflicts = self.search(domain)
            booking.conflict_ids = conflicts
            booking.has_conflicts = len(conflicts) > 0

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        """Kiểm tra logic ngày giờ"""
        for booking in self:
            if booking.end_datetime <= booking.start_datetime:
                raise ValidationError(_('Thời gian kết thúc phải sau thời gian bắt đầu!'))
            
            # Kiểm tra thời lượng tối thiểu/tối đa
            if booking.room_id:
                if booking.duration < booking.room_id.min_booking_duration:
                    raise ValidationError(
                        _('Thời lượng tối thiểu cho phòng này là %.1f giờ!') 
                        % booking.room_id.min_booking_duration
                    )
                if booking.duration > booking.room_id.max_booking_duration:
                    raise ValidationError(
                        _('Thời lượng tối đa cho phòng này là %.1f giờ!') 
                        % booking.room_id.max_booking_duration
                    )

    @api.constrains('num_attendees', 'room_id')
    def _check_capacity(self):
        """Kiểm tra sức chứa phòng"""
        for booking in self:
            if booking.room_id and booking.num_attendees > booking.room_id.capacity:
                raise ValidationError(
                    _('Số người tham dự (%d) vượt quá sức chứa của phòng (%d)!') 
                    % (booking.num_attendees, booking.room_id.capacity)
                )

    @api.constrains('start_datetime', 'end_datetime', 'room_id', 'state')
    def _check_conflicts(self):
        """Kiểm tra xung đột đặt phòng"""
        for booking in self:
            if booking.state in ['cancelled', 'draft']:
                continue
            
            if not booking.room_id or not booking.start_datetime or not booking.end_datetime:
                continue
            
            available, conflicts = booking.room_id.check_availability(
                booking.start_datetime,
                booking.end_datetime,
                exclude_booking_id=booking.id
            )
            
            if not available:
                conflict_names = ', '.join(conflicts.mapped('name'))
                raise ValidationError(
                    _('Phòng "%s" đã bị đặt vào khoảng thời gian này!\n\nXung đột với: %s') 
                    % (booking.room_id.name, conflict_names)
                )

    def action_submit(self):
        """Gửi yêu cầu đặt phòng và tạo văn bản đến để trình duyệt"""
        for booking in self:
            booking.write({'state': 'submitted'})
            booking.message_post(body=_('Yêu cầu đặt phòng đã được gửi'))
            
            # Tự động tạo văn bản đến yêu cầu duyệt
            booking._create_approval_van_ban_den()

    def action_confirm(self):
        """Xác nhận đặt phòng và tạo phiếu mượn tài sản tự động"""
        # Nếu đang duyệt từ văn bản đến, cho phép tiếp tục
        if not self.env.context.get('from_van_ban_approval'):
            # Kiểm tra xem có văn bản chờ duyệt không
            for booking in self:
                pending_van_ban = self.env['van_ban_den'].search([
                    ('source_model', '=', booking._name),
                    ('source_res_id', '=', booking.id),
                    ('request_type', '=', 'booking_approval'),
                    ('approval_state', '=', 'pending'),
                ], limit=1)
                if pending_van_ban:
                    raise UserError(_('Yêu cầu đặt phòng này đang chờ Ban Giám đốc duyệt.\nVui lòng đợi phê duyệt từ văn bản: %s') % pending_van_ban.ten_van_ban)
        
        for booking in self:
            # Kiểm tra lại xung đột
            available, conflicts = booking.room_id.check_availability(
                booking.start_datetime,
                booking.end_datetime,
                exclude_booking_id=booking.id
            )
            
            if not available:
                raise ValidationError(_('Phòng không còn khả dụng trong khoảng thời gian này!'))
            
            booking.write({'state': 'confirmed'})
            booking._create_calendar_event()
            
            # Tạo phiếu mượn tài sản tự động cho các thiết bị được chọn
            if booking.required_equipment_ids:
                booking._create_auto_lending_records()
            
            # Tích hợp Zoom nếu là họp online
            if booking.meeting_type == 'online':
                booking._create_zoom_meeting()
            
            # Tích hợp Google Calendar
            booking._create_google_calendar_event()
            
            # Gửi email xác nhận
            booking._send_confirmation_email()
            
            # Gửi email thông báo cho tất cả người tham dự
            booking._send_notification_emails()
            
            booking.message_post(body=_('Đặt phòng đã được xác nhận'))
        
        # Thông báo và chuyển về calendar
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã duyệt %s lịch đặt phòng. Email thông báo đã được gửi đến người tổ chức và người tham dự.') % len(self),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_direct_approve(self):
        """Duyệt đặt phòng trực tiếp từ tree view và cập nhật văn bản đến"""
        for booking in self:
            if booking.state != 'submitted':
                continue
            
            # Tìm văn bản đến liên quan và cập nhật
            pending_van_ban = self.env['van_ban_den'].search([
                ('source_model', '=', booking._name),
                ('source_res_id', '=', booking.id),
                ('request_type', '=', 'booking_approval'),
                ('approval_state', '=', 'pending'),
            ], limit=1)
            
            if pending_van_ban:
                # Lấy người duyệt hiện tại
                current_user = self.env.user
                approver = self.env['nhan_vien'].search([
                    ('user_id', '=', current_user.id)
                ], limit=1) or pending_van_ban.approver_id
                
                # Cập nhật văn bản đến thành đã duyệt với chữ ký
                pending_van_ban.write({
                    'approval_state': 'approved',
                    'approval_date': fields.Datetime.now(),
                    'signer_employee_id': approver.id if approver else False,
                    'signature_date': fields.Datetime.now(),
                })
                
                # Tạo văn bản đi phản hồi
                pending_van_ban._create_van_ban_di_response()
                
                # Thông báo cho người yêu cầu
                pending_van_ban._notify_requester(approved=True)
                
                pending_van_ban.message_post(body=_('✅ Đã được DUYỆT và KÝ từ trang Duyệt đặt phòng bởi %s') % self.env.user.name)
            
            # Xác nhận booking với context để bỏ qua check văn bản
            booking.with_context(from_van_ban_approval=True).action_confirm()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã duyệt %s lịch đặt phòng. Calendar và Google Calendar đã được cập nhật.') % len(self),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_direct_reject(self):
        """Từ chối đặt phòng trực tiếp từ tree view và cập nhật văn bản đến"""
        for booking in self:
            if booking.state != 'submitted':
                continue
            
            # Tìm văn bản đến liên quan và cập nhật
            pending_van_ban = self.env['van_ban_den'].search([
                ('source_model', '=', booking._name),
                ('source_res_id', '=', booking.id),
                ('request_type', '=', 'booking_approval'),
                ('approval_state', '=', 'pending'),
            ], limit=1)
            
            if pending_van_ban:
                # Lấy người duyệt hiện tại
                current_user = self.env.user
                approver = self.env['nhan_vien'].search([
                    ('user_id', '=', current_user.id)
                ], limit=1) or pending_van_ban.approver_id
                
                # Cập nhật văn bản đến thành từ chối
                pending_van_ban.write({
                    'approval_state': 'rejected',
                    'approval_date': fields.Datetime.now(),
                    'approval_note': 'Từ chối từ trang Duyệt đặt phòng bởi ' + self.env.user.name,
                    'signer_employee_id': approver.id if approver else False,
                })
                pending_van_ban._notify_requester(approved=False)
                pending_van_ban.message_post(body=_('❌ Đã bị TỪ CHỐI từ trang Duyệt đặt phòng bởi %s') % self.env.user.name)
            
            # Hủy booking
            booking.write({
                'state': 'cancelled',
                'cancellation_reason': 'Bị từ chối bởi ' + self.env.user.name,
            })
            booking.message_post(body=_('Yêu cầu đặt phòng đã bị từ chối'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã từ chối'),
                'message': _('Đã từ chối %s yêu cầu đặt phòng') % len(self),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Hủy đặt phòng hoặc từ chối yêu cầu"""
        for booking in self:
            old_state = booking.state
            booking.write({'state': 'cancelled'})
            
            # Xóa calendar event
            if booking.calendar_event_id:
                booking.calendar_event_id.unlink()
            
            # Xóa Zoom meeting
            if booking.zoom_meeting_id:
                booking._delete_zoom_meeting()
            
            # Xóa Google Calendar event
            if booking.google_calendar_event_id:
                booking._delete_google_calendar_event()
            
            booking._send_cancellation_email()
            if old_state == 'submitted':
                booking.message_post(body=_('Yêu cầu đặt phòng đã bị từ chối: %s') % (booking.cancellation_reason or ''))
            else:
                booking.message_post(body=_('Đặt phòng đã bị hủy: %s') % (booking.cancellation_reason or ''))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã từ chối'),
                'message': _('Đã từ chối %s yêu cầu đặt phòng') % len(self),
                'type': 'warning',
            }
        }

    def action_checkin(self):
        """Check-in vào phòng"""
        self.ensure_one()
        
        if not self.can_checkin:
            raise UserError(_('Không thể check-in vào lúc này!'))
        
        self.write({
            'checkin_datetime': fields.Datetime.now(),
            'checkin_by': self.env.user.id,
            'state': 'in_progress',
        })
        self.message_post(body=_('Đã check-in vào phòng'))

    def action_checkout(self):
        """Check-out khỏi phòng"""
        self.ensure_one()
        
        if not self.checkin_datetime:
            raise UserError(_('Chưa check-in!'))
        
        self.write({
            'checkout_datetime': fields.Datetime.now(),
            'state': 'done',
        })
        self.message_post(body=_('Đã check-out khỏi phòng'))

    def action_suggest_alternatives(self):
        """Gợi ý phòng thay thế khi xung đột"""
        self.ensure_one()
        
        # Tìm các phòng phù hợp
        suitable_rooms = self.env['dnu.meeting.room'].search([
            ('state', '=', 'available'),
            ('capacity', '>=', self.num_attendees),
            ('id', '!=', self.room_id.id),
        ])
        
        available_rooms = []
        for room in suitable_rooms:
            available, _ = room.check_availability(self.start_datetime, self.end_datetime)
            if available:
                available_rooms.append(room.id)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gợi ý phòng thay thế',
            'res_model': 'dnu.meeting.room',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', available_rooms)],
        }

    def _create_approval_van_ban_den(self):
        """Tạo văn bản đến yêu cầu duyệt đặt phòng và gửi đến Ban Giám đốc"""
        self.ensure_one()
        
        # Kiểm tra xem đã có văn bản yêu cầu duyệt chưa
        existing = self.env['van_ban_den'].search([
            ('source_model', '=', self._name),
            ('source_res_id', '=', self.id),
            ('request_type', '=', 'booking_approval'),
            ('approval_state', 'in', ['draft', 'pending']),
        ], limit=1)
        
        if existing:
            return existing
        
        # Tạo văn bản đến yêu cầu duyệt
        note = 'Yêu cầu duyệt đặt phòng họp:\n'
        note += '- Phòng: %s\n' % self.room_id.name
        note += '- Chủ đề: %s\n' % self.subject
        note += '- Thời gian: %s - %s\n' % (
            self.start_datetime.strftime('%d/%m/%Y %H:%M') if self.start_datetime else '',
            self.end_datetime.strftime('%d/%m/%Y %H:%M') if self.end_datetime else ''
        )
        note += '- Số người: %s\n' % self.num_attendees
        note += '- Người tổ chức: %s\n' % self.organizer_name
        
        if self.required_equipment_ids:
            note += '- Thiết bị cần mượn: %s\n' % ', '.join(self.required_equipment_ids.mapped('name'))
        
        van_ban = self.env['van_ban_den'].create_approval_request(
            source_record=self,
            request_type='booking_approval',
            note=note,
        )
        
        self.message_post(body=_('Đã tạo văn bản yêu cầu duyệt: %s') % van_ban.ten_van_ban)
        
        return van_ban

    def _create_calendar_event(self):
        """Tạo sự kiện lịch"""
        for booking in self:
            if booking.calendar_event_id:
                continue
            
            partner_ids = []
            for attendee in booking.attendee_ids:
                if attendee.user_id:
                    partner_ids.append(attendee.user_id.partner_id.id)
            
            event = self.env['calendar.event'].create({
                'name': '%s - %s' % (booking.name, booking.subject),
                'start': booking.start_datetime,
                'stop': booking.end_datetime,
                'location': booking.room_id.name,
                'description': booking.description or '',
                'partner_ids': [(6, 0, partner_ids)],
                'user_id': booking.organizer_id.user_id.id if booking.organizer_id.user_id else self.env.user.id,
            })
            
            booking.calendar_event_id = event.id
    
    def _create_auto_lending_records(self):
        """Tạo phiếu mượn tự động cho các thiết bị trong booking"""
        self.ensure_one()
        
        if not self.required_equipment_ids:
            return
        
        # Xác định người mượn (ưu tiên nhan_vien, fallback sang HR employee)
        nhan_vien_muon = self.nhan_vien_to_chuc_id
        borrower = self.organizer_id
        
        if not borrower and not nhan_vien_muon:
            raise UserError(_('Không xác định được người tổ chức để tạo phiếu mượn!'))
        
        # Nếu chỉ có nhan_vien mà không có HR employee, tìm HR employee tương ứng
        if nhan_vien_muon and not borrower:
            borrower = nhan_vien_muon.hr_employee_id
            if not borrower:
                raise UserError(_('Người tổ chức "%s" chưa có liên kết với hệ thống HR!') % nhan_vien_muon.ho_va_ten)
        
        # Tạo phiếu mượn cho từng thiết bị
        created_lendings = self.env['dnu.asset.lending']
        skipped_equipments = []
        
        for equipment in self.required_equipment_ids:
            # Kiểm tra xem đã tạo phiếu mượn chưa
            existing_lending = self.env['dnu.asset.lending'].search([
                ('booking_id', '=', self.id),
                ('asset_id', '=', equipment.id),
                ('state', 'not in', ['cancelled', 'returned'])
            ], limit=1)
            
            if existing_lending:
                continue  # Đã tồn tại phiếu mượn
            
            # Kiểm tra xem tài sản có đang được mượn không
            conflicting_lending = self.env['dnu.asset.lending'].search([
                ('asset_id', '=', equipment.id),
                ('state', 'in', ['approved', 'borrowed']),
                ('date_borrow', '<', self.end_datetime),
                ('date_expected_return', '>', self.start_datetime),
            ], limit=1)
            
            if conflicting_lending:
                # Tài sản đang được mượn, bỏ qua
                skipped_equipments.append({
                    'name': equipment.name,
                    'borrower': conflicting_lending.borrower_name,
                    'return_date': conflicting_lending.date_expected_return
                })
                continue
            
            # Tạo phiếu mượn mới - điền cả borrower_id và nhan_vien_muon_id
            lending_vals = {
                'asset_id': equipment.id,
                'borrower_id': borrower.id if borrower else False,
                'nhan_vien_muon_id': nhan_vien_muon.id if nhan_vien_muon else False,
                'date_borrow': self.start_datetime,
                'date_expected_return': self.end_datetime,
                'purpose': 'meeting',
                'purpose_note': 'Mượn tài sản cho cuộc họp: %s\n%s' % (
                    self.subject,
                    self.description or ''
                ),
                'booking_id': self.id,
                'location': self.room_id.name,
                'state': 'draft',
                'is_auto_created': True,
                'require_approval': equipment.state == 'assigned',  # Chỉ yêu cầu phê duyệt nếu đã gán
            }
            
            lending = self.env['dnu.asset.lending'].create(lending_vals)
            created_lendings |= lending
            
            # Tự động gửi yêu cầu mượn và tạo biên bản
            try:
                lending.action_request()
            except Exception as e:
                # Log lỗi nhưng không block booking
                self.message_post(
                    body=_('Lỗi khi tạo yêu cầu mượn cho tài sản "%s": %s') % (equipment.name, str(e))
                )
        
        # Thông báo về tài sản bị bỏ qua
        if skipped_equipments:
            skip_msg = _('<b>Cảnh báo:</b> Các tài sản sau đang được mượn và không thể tạo phiếu:<br/><ul>')
            for skip in skipped_equipments:
                skip_msg += _('<li><b>%s</b> - Đang mượn bởi <i>%s</i> đến %s</li>') % (
                    skip['name'],
                    skip['borrower'],
                    skip['return_date'].strftime('%d/%m/%Y %H:%M') if skip['return_date'] else ''
                )
            skip_msg += '</ul>'
            self.message_post(body=skip_msg, subtype_xmlid='mail.mt_warning')
        
        # Thông báo số phiếu mượn đã tạo
        if created_lendings:
            self.message_post(
                body=_('Đã tạo %d phiếu mượn tài sản tự động. Vui lòng chờ người quản lý tài sản ký duyệt biên bản bàn giao.') % 
                len(created_lendings),
                subtype_xmlid='mail.mt_note'
            )
            
            # Tạo activity nhắc nhở người tổ chức
            if borrower.user_id:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=borrower.user_id.id,
                    summary=_('Chờ phê duyệt mượn tài sản'),
                    note=_('Đã tạo %d phiếu mượn tài sản cho cuộc họp "%s". '
                           'Vui lòng chờ người quản lý tài sản ký duyệt biên bản bàn giao. '
                           'Bạn có thể xem trạng thái tại tab Mượn tài sản.') % (
                        len(created_lendings), self.subject
                    )
                )

    def _update_calendar_event(self):
        """Cập nhật sự kiện lịch"""
        for booking in self:
            if not booking.calendar_event_id:
                continue
            
            booking.calendar_event_id.write({
                'name': '%s - %s' % (booking.name, booking.subject),
                'start': booking.start_datetime,
                'stop': booking.end_datetime,
                'location': booking.room_id.name,
                'description': booking.description or '',
            })

    def _get_admin_emails(self):
        """Lấy danh sách email admin để CC"""
        admin_emails = []
        # Lấy từ System Parameters nếu có
        admin_email_param = self.env['ir.config_parameter'].sudo().get_param('dnu_meeting_asset.admin_notification_email')
        if admin_email_param:
            admin_emails.extend([e.strip() for e in admin_email_param.split(',') if e.strip()])
        # Mặc định thêm email admin hệ thống
        admin_users = self.env['res.users'].sudo().search([('groups_id', 'in', self.env.ref('base.group_system').id)])
        for user in admin_users:
            if user.email and user.email not in admin_emails:
                admin_emails.append(user.email)
        return admin_emails

    def _send_email_with_tracking(self, template_xmlid, recipient_emails, event_type='notification'):
        """Gửi email và lưu lịch sử"""
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning(f"Email template {template_xmlid} không tồn tại")
            return False
        
        sent_count = 0
        failed_count = 0
        for email in recipient_emails:
            if not email:
                continue
            try:
                template.send_mail(self.id, force_send=True, email_values={
                    'email_to': email
                })
                sent_count += 1
                _logger.info(f"[Booking {self.name}] Email {event_type} đã gửi thành công đến {email}")
            except Exception as e:
                failed_count += 1
                _logger.error(f"[Booking {self.name}] Lỗi gửi email {event_type} đến {email}: {str(e)}")
        
        if sent_count > 0:
            # Cập nhật tracking fields
            self.write({
                'email_send_count': self.email_send_count + sent_count,
                'last_email_sent': fields.Datetime.now(),
            })
            self.message_post(
                body=_('📧 [%s] Đã gửi %d/%d email thông báo thành công') % (event_type.upper(), sent_count, sent_count + failed_count),
                message_type='notification'
            )
            _logger.info(f"[Booking {self.name}] Gửi {sent_count}/{sent_count + failed_count} email {event_type} thành công")
        elif failed_count > 0:
            self.message_post(
                body=_('⚠️ [%s] Gửi email thất bại (%d email)') % (event_type.upper(), failed_count),
                message_type='notification'
            )
        return sent_count > 0

    def _send_confirmation_email(self):
        """Gửi email xác nhận cho người tổ chức, người tham dự và admin"""
        template = self.env.ref('dnu_meeting_asset.email_template_booking_confirmation', raise_if_not_found=False)
        if not template:
            return
        
        for booking in self:
            recipients = []
            
            # Email người tổ chức
            if booking.organizer_id and booking.organizer_id.work_email:
                recipients.append(booking.organizer_id.work_email)
            
            # Email người tham dự
            for attendee in booking.attendee_ids:
                if attendee.work_email and attendee.work_email not in recipients:
                    recipients.append(attendee.work_email)
            
            # Email admin
            admin_emails = booking._get_admin_emails()
            for email in admin_emails:
                if email not in recipients:
                    recipients.append(email)
            
            # Gửi email
            booking._send_email_with_tracking(
                'dnu_meeting_asset.email_template_booking_confirmation',
                recipients,
                'XÁC NHẬN BOOKING'
            )

    def _send_cancellation_email(self):
        """Gửi email thông báo hủy cho tất cả người liên quan"""
        template = self.env.ref('dnu_meeting_asset.email_template_booking_cancellation', raise_if_not_found=False)
        if not template:
            return
        
        for booking in self:
            recipients = []
            
            # Email người tổ chức
            if booking.organizer_id and booking.organizer_id.work_email:
                recipients.append(booking.organizer_id.work_email)
            
            # Email người tham dự
            for attendee in booking.attendee_ids:
                if attendee.work_email and attendee.work_email not in recipients:
                    recipients.append(attendee.work_email)
            
            # Email admin
            admin_emails = booking._get_admin_emails()
            for email in admin_emails:
                if email not in recipients:
                    recipients.append(email)
            
            # Gửi email
            booking._send_email_with_tracking(
                'dnu_meeting_asset.email_template_booking_cancellation',
                recipients,
                'HỦY BOOKING'
            )

    def _send_created_notification_email(self):
        """Gửi email thông báo tạo booking cho người tổ chức, người tham dự và admin"""
        self.ensure_one()
        if self.state == 'cancelled':
            return
        
        recipients = []
        
        # Email người tổ chức
        if self.organizer_id and self.organizer_id.work_email:
            recipients.append(self.organizer_id.work_email)
        
        # Email người tham dự
        for attendee in self.attendee_ids:
            if attendee.work_email and attendee.work_email not in recipients:
                recipients.append(attendee.work_email)
        
        # Email admin
        admin_emails = self._get_admin_emails()
        for email in admin_emails:
            if email not in recipients:
                recipients.append(email)
        
        # Gửi email
        self._send_email_with_tracking(
            'dnu_meeting_asset.email_template_booking_created',
            recipients,
            'TẠO BOOKING'
        )

    @api.model
    def _cron_auto_checkout(self):
        """Tự động check-out các booking đã qua giờ"""
        now = fields.Datetime.now()
        bookings = self.search([
            ('state', '=', 'in_progress'),
            ('end_datetime', '<', now),
        ])
        for booking in bookings:
            booking.action_checkout()

    @api.model
    def _cron_send_reminders(self):
        """Gửi nhắc nhở trước 30 phút"""
        now = fields.Datetime.now()
        reminder_time = now + timedelta(minutes=30)
        
        bookings = self.search([
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', now),
            ('start_datetime', '<=', reminder_time),
        ])
        
        template = self.env.ref('dnu_meeting_asset.email_template_booking_reminder', raise_if_not_found=False)
        if template:
            for booking in bookings:
                template.send_mail(booking.id, force_send=True)

    # ==================== ZOOM INTEGRATION ====================
    
    def _create_zoom_meeting(self):
        """Tạo cuộc họp Zoom"""
        self.ensure_one()
        
        try:
            zoom = self.env['zoom.integration'].get_active_integration()
        except UserError:
            # Không có cấu hình Zoom, bỏ qua
            return
        
        duration_minutes = int(self.duration * 60)
        description = self.description or self.subject
        
        result = zoom.create_meeting(
            topic=f"{self.name} - {self.subject}",
            start_time=self.start_datetime,
            duration_minutes=duration_minutes,
            description=description,
        )
        
        if result.get('success'):
            self.write({
                'zoom_meeting_id': str(result.get('meeting_id')),
                'zoom_join_url': result.get('join_url'),
                'zoom_start_url': result.get('start_url'),
                'zoom_password': result.get('password'),
                'zoom_sync_status': 'synced',
            })
            self.message_post(body=_(
                '✅ Đã tạo Zoom meeting thành công!\n'
                '🔗 Link tham gia: %s\n'
                '🔑 Meeting ID: %s'
            ) % (result.get('join_url'), result.get('meeting_id')))
        else:
            self.write({'zoom_sync_status': 'error'})
            self.message_post(body=_('❌ Lỗi khi tạo Zoom meeting: %s') % result.get('error'))
    
    def _update_zoom_meeting(self):
        """Cập nhật cuộc họp Zoom"""
        self.ensure_one()
        
        if not self.zoom_meeting_id:
            return
        
        try:
            zoom = self.env['zoom.integration'].get_active_integration()
        except UserError:
            return
        
        duration_minutes = int(self.duration * 60)
        
        result = zoom.update_meeting(
            meeting_id=self.zoom_meeting_id,
            topic=f"{self.name} - {self.subject}",
            start_time=self.start_datetime,
            duration_minutes=duration_minutes,
        )
        
        if result.get('success'):
            self.message_post(body=_('✅ Đã cập nhật Zoom meeting'))
        else:
            self.message_post(body=_('❌ Lỗi khi cập nhật Zoom meeting: %s') % result.get('error'))
    
    def _delete_zoom_meeting(self):
        """Xóa cuộc họp Zoom"""
        self.ensure_one()
        
        if not self.zoom_meeting_id:
            return
        
        try:
            zoom = self.env['zoom.integration'].get_active_integration()
            result = zoom.delete_meeting(self.zoom_meeting_id)
            
            if result.get('success'):
                self.write({
                    'zoom_meeting_id': False,
                    'zoom_join_url': False,
                    'zoom_start_url': False,
                    'zoom_password': False,
                    'zoom_sync_status': 'not_synced',
                })
                self.message_post(body=_('✅ Đã xóa Zoom meeting'))
        except UserError:
            pass
    
    def action_create_zoom_meeting(self):
        """Button để tạo Zoom meeting thủ công"""
        self.ensure_one()
        if self.meeting_type != 'online':
            raise UserError(_('Chỉ có thể tạo Zoom meeting cho cuộc họp trực tuyến!'))
        if self.zoom_meeting_id:
            raise UserError(_('Đã có Zoom meeting cho cuộc họp này!'))
        self._create_zoom_meeting()
    
    def action_open_zoom_meeting(self):
        """Mở link Zoom meeting"""
        self.ensure_one()
        if not self.zoom_join_url:
            raise UserError(_('Chưa có link Zoom meeting!'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.zoom_join_url,
            'target': 'new',
        }
    
    def action_view_room_bookings(self):
        """Xem tất cả lịch đặt của phòng này"""
        self.ensure_one()
        return {
            'name': _('Lịch đặt phòng - %s') % self.room_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.meeting.booking',
            'view_mode': 'calendar,tree,form',
            'domain': [('room_id', '=', self.room_id.id)],
            'context': {
                'default_room_id': self.room_id.id,
                'search_default_confirmed': 1,
            },
        }
    
    # ==================== GOOGLE CALENDAR INTEGRATION ====================
    
    def _get_attendee_emails(self):
        """Lấy danh sách email người tham dự"""
        emails = []
        for attendee in self.attendee_ids:
            if attendee.work_email:
                emails.append(attendee.work_email)
            elif attendee.user_id and attendee.user_id.email:
                emails.append(attendee.user_id.email)
        
        # Thêm email người tổ chức
        if self.organizer_id:
            if self.organizer_id.work_email:
                emails.append(self.organizer_id.work_email)
            elif self.organizer_id.user_id and self.organizer_id.user_id.email:
                emails.append(self.organizer_id.user_id.email)
        
        return list(set(emails))  # Loại bỏ trùng lặp
    
    def _create_google_calendar_event(self):
        """Tạo sự kiện trên Google Calendar"""
        self.ensure_one()
        
        try:
            gcal = self.env['google.calendar.integration'].get_active_integration()
        except UserError:
            # Không có cấu hình Google Calendar, bỏ qua
            return
        
        # Chuẩn bị mô tả
        description = f"📋 {self.subject}\n\n"
        if self.description:
            description += f"{self.description}\n\n"
        description += f"📍 Phòng họp: {self.room_id.name}\n"
        description += f"👤 Người tổ chức: {self.organizer_name}\n"
        description += f"👥 Số người tham dự: {self.num_attendees}\n"

        if self.event_meeting_room_url or self.event_meeting_room_website_url:
            jitsi_link = self.event_meeting_room_url or self.event_meeting_room_website_url
            description += f"\n🔗 Link phòng Jitsi: {jitsi_link}\n"
        
        # Lấy location
        location = self.room_id.name
        if self.room_id.location:
            location = f"{self.room_id.name} - {self.room_id.location}"
        
        # Lấy link họp (ưu tiên Jitsi nếu có, sau đó Zoom)
        meeting_link = self.event_meeting_room_url or self.event_meeting_room_website_url
        if not meeting_link and self.meeting_type == 'online':
            meeting_link = self.zoom_join_url
        
        result = gcal.create_event(
            summary=f"{self.name} - {self.subject}",
            start_datetime=self.start_datetime,
            end_datetime=self.end_datetime,
            description=description,
            location=location,
            attendees=self._get_attendee_emails(),
            meeting_link=meeting_link,
        )
        
        if result.get('success'):
            self.write({
                'google_calendar_event_id': result.get('event_id'),
                'google_calendar_link': result.get('html_link'),
                'google_sync_status': 'synced',
            })
            self.message_post(body=_(
                '✅ Đã đồng bộ lên Google Calendar!\n'
                '🔗 Link: %s'
            ) % result.get('html_link'))
        else:
            self.write({'google_sync_status': 'error'})
            self.message_post(body=_('❌ Lỗi khi tạo Google Calendar event: %s') % result.get('error'))
    
    def _update_google_calendar_event(self):
        """Cập nhật sự kiện trên Google Calendar"""
        self.ensure_one()
        
        if not self.google_calendar_event_id:
            return
        
        try:
            gcal = self.env['google.calendar.integration'].get_active_integration()
        except UserError:
            return
        
        description = f"📋 {self.subject}\n\n"
        if self.description:
            description += f"{self.description}\n\n"
        if self.event_meeting_room_url or self.event_meeting_room_website_url:
            jitsi_link = self.event_meeting_room_url or self.event_meeting_room_website_url
            description += f"\n🔗 Link phòng Jitsi: {jitsi_link}\n"
        if self.zoom_join_url:
            description += f"\n🔗 Link họp Zoom: {self.zoom_join_url}\n"
        
        location = self.room_id.name
        if self.room_id.location:
            location = f"{self.room_id.name} - {self.room_id.location}"
        
        result = gcal.update_event(
            event_id=self.google_calendar_event_id,
            summary=f"{self.name} - {self.subject}",
            start_datetime=self.start_datetime,
            end_datetime=self.end_datetime,
            description=description,
            location=location,
            attendees=self._get_attendee_emails(),
        )
        
        if result.get('success'):
            self.message_post(body=_('✅ Đã cập nhật Google Calendar event'))
        else:
            self.message_post(body=_('❌ Lỗi khi cập nhật Google Calendar event: %s') % result.get('error'))
    
    def _delete_google_calendar_event(self):
        """Xóa sự kiện trên Google Calendar"""
        self.ensure_one()
        
        if not self.google_calendar_event_id:
            return
        
        try:
            gcal = self.env['google.calendar.integration'].get_active_integration()
            result = gcal.delete_event(self.google_calendar_event_id)
            
            if result.get('success'):
                self.write({
                    'google_calendar_event_id': False,
                    'google_calendar_link': False,
                    'google_sync_status': 'not_synced',
                })
                self.message_post(body=_('✅ Đã xóa Google Calendar event'))
        except UserError:
            pass
    
    def action_sync_google_calendar(self):
        """Button để đồng bộ Google Calendar thủ công"""
        self.ensure_one()
        if self.google_calendar_event_id:
            self._update_google_calendar_event()
        else:
            self._create_google_calendar_event()
    
    def action_open_google_calendar(self):
        """Mở link Google Calendar"""
        self.ensure_one()
        if not self.google_calendar_link:
            raise UserError(_('Chưa có link Google Calendar!'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.google_calendar_link,
            'target': 'new',
        }

    # ==================== EMAIL NOTIFICATION METHODS ====================
    
    def _send_notification_emails(self):
        """Gửi email thông báo đến tất cả người tham dự và admin"""
        self.ensure_one()
        
        # Kiểm tra xem đã gửi email chưa (nếu field tồn tại)
        if hasattr(self, 'confirmation_email_sent') and self.confirmation_email_sent:
            return
        
        recipients = []
        
        # Email người tổ chức
        if self.organizer_id and self.organizer_id.work_email:
            recipients.append(self.organizer_id.work_email)
        
        # Email người tham dự
        for attendee in self.attendee_ids:
            if attendee.work_email and attendee.work_email not in recipients:
                recipients.append(attendee.work_email)
        
        # Email admin
        admin_emails = self._get_admin_emails()
        for email in admin_emails:
            if email not in recipients:
                recipients.append(email)
        
        # Gửi email
        self._send_email_with_tracking(
            'dnu_meeting_asset.email_template_booking_confirmation',
            recipients,
            'THÔNG BÁO BOOKING'
        )
        
        # Đánh dấu đã gửi (nếu field tồn tại)
        if hasattr(self, 'confirmation_email_sent'):
            self.write({'confirmation_email_sent': True})
    
    def _send_update_notification_email(self):
        """Gửi email thông báo khi có cập nhật cho người tổ chức, người tham dự và admin"""
        self.ensure_one()
        if self.state == 'cancelled':
            return
        
        recipients = []
        
        # Email người tổ chức
        if self.organizer_id and self.organizer_id.work_email:
            recipients.append(self.organizer_id.work_email)
        
        # Email người tham dự
        for attendee in self.attendee_ids:
            if attendee.work_email and attendee.work_email not in recipients:
                recipients.append(attendee.work_email)
        
        # Email admin
        admin_emails = self._get_admin_emails()
        for email in admin_emails:
            if email not in recipients:
                recipients.append(email)
        
        # Gửi email
        self._send_email_with_tracking(
            'dnu_meeting_asset.email_template_meeting_update',
            recipients,
            'CẬP NHẬT BOOKING'
        )
    
    @api.model
    def _cron_send_email_reminders(self):
        """Cron job: Gửi email nhắc lịch họp 30 phút trước"""
        from datetime import timedelta
        
        now = fields.Datetime.now()
        reminder_time = now + timedelta(minutes=30)
        
        # Tìm các booking sắp diễn ra trong 30-35 phút tới
        domain = [
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', now),
            ('start_datetime', '<=', reminder_time),
        ]
        
        # Nếu field reminder_email_sent tồn tại, thêm vào domain
        if 'reminder_email_sent' in self._fields:
            domain.append(('reminder_email_sent', '=', False))
        
        bookings = self.search(domain)
        
        for booking in bookings:
            try:
                recipients = []
                
                # Email người tổ chức
                if booking.organizer_id and booking.organizer_id.work_email:
                    recipients.append(booking.organizer_id.work_email)
                
                # Email người tham dự
                for attendee in booking.attendee_ids:
                    if attendee.work_email and attendee.work_email not in recipients:
                        recipients.append(attendee.work_email)
                
                # Email admin
                admin_emails = booking._get_admin_emails()
                for email in admin_emails:
                    if email not in recipients:
                        recipients.append(email)
                
                # Gửi email
                if recipients:
                    booking._send_email_with_tracking(
                        'dnu_meeting_asset.email_template_meeting_reminder',
                        recipients,
                        'NHẮC LỊCH HỌP'
                    )
                
                # Đánh dấu đã gửi (nếu field tồn tại)
                if 'reminder_email_sent' in booking._fields:
                    booking.write({'reminder_email_sent': True})
                
            except Exception as e:
                _logger.error(f"Error sending reminder email for booking {booking.name}: {str(e)}")
                continue

    def action_send_email_notification(self):
        """Button để gửi email thông báo thủ công"""
        self.ensure_one()
        recipients = []
        
        # Email người tổ chức
        if self.organizer_id and self.organizer_id.work_email:
            recipients.append(self.organizer_id.work_email)
        
        # Email người tham dự
        for attendee in self.attendee_ids:
            if attendee.work_email and attendee.work_email not in recipients:
                recipients.append(attendee.work_email)
        
        # Email admin
        admin_emails = self._get_admin_emails()
        for email in admin_emails:
            if email not in recipients:
                recipients.append(email)
        
        if not recipients:
            raise UserError(_('Không có người nhận email. Vui lòng kiểm tra email của người tổ chức và người tham dự.'))
        
        # Gửi email
        if self.state == 'confirmed':
            template_id = 'dnu_meeting_asset.email_template_booking_confirmation'
            event_type = 'XÁC NHẬN BOOKING'
        elif self.state == 'cancelled':
            template_id = 'dnu_meeting_asset.email_template_booking_cancellation'
            event_type = 'HỦY BOOKING'
        else:
            template_id = 'dnu_meeting_asset.email_template_booking_created'
            event_type = 'TẠO BOOKING'
        
        sent = self._send_email_with_tracking(template_id, recipients, event_type)
        
        if sent:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã gửi email thông báo đến %d người: %s') % (len(recipients), ', '.join(recipients)),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_('Không thể gửi email. Vui lòng kiểm tra cấu hình email.'))
    
    def _get_attendee_emails(self):
        """Lấy danh sách email của người tham dự"""
        self.ensure_one()
        emails = []
        
        # Email người tổ chức
        if self.organizer_id and self.organizer_id.work_email:
            emails.append(self.organizer_id.work_email)
        
        # Email người tham dự
        for attendee in self.attendee_ids:
            if attendee.work_email:
                emails.append(attendee.work_email)
        
        return emails
    
    # ==================== AI Integration Methods ====================
    
    def action_ai_generate_summary(self):
        """Mở wizard AI tạo biên bản cuộc họp"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '📝 AI Tạo biên bản',
            'res_model': 'ai.meeting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'summary',
                'default_booking_id': self.id,
                'default_meeting_notes': self.notes,
                'ai_context_model': self._name,
                'ai_context_res_id': self.id,
            }
        }
    
    def action_ai_generate_agenda(self):
        """Mở wizard AI tạo agenda cuộc họp"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '📋 AI Tạo agenda',
            'res_model': 'ai.meeting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'agenda',
                'default_meeting_subject': self.subject,
                'default_meeting_description': self.description,
                'default_duration_hours': self.duration or 1.0,
                'ai_context_model': self._name,
                'ai_context_res_id': self.id,
            }
        }
