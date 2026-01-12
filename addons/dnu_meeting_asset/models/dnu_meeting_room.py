# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MeetingRoom(models.Model):
    _name = 'dnu.meeting.room'
    _description = 'Phòng họp'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Tên phòng họp',
        required=True,
        tracking=True
    )
    code = fields.Char(
        string='Mã phòng',
        required=True,
        copy=False,
        tracking=True
    )
    capacity = fields.Integer(
        string='Sức chứa',
        default=0,
        required=True,
        tracking=True,
        help='Số người tối đa'
    )
    location = fields.Char(
        string='Vị trí',
        tracking=True,
        help='Ví dụ: Tầng 2, Toà A'
    )
    floor = fields.Char(string='Tầng')
    building = fields.Char(string='Tòa nhà')
    
    # Equipment
    equipment_ids = fields.Many2many(
        'dnu.asset',
        'room_asset_rel',
        'room_id',
        'asset_id',
        string='Trang thiết bị',
        help='Thiết bị cố định trong phòng'
    )
    
    # Facilities
    has_projector = fields.Boolean(string='Máy chiếu')
    has_tv = fields.Boolean(string='TV')
    has_whiteboard = fields.Boolean(string='Bảng trắng')
    has_video_conference = fields.Boolean(string='Hệ thống họp trực tuyến')
    has_air_conditioning = fields.Boolean(string='Điều hòa')
    has_wifi = fields.Boolean(string='WiFi')
    
    # Status
    state = fields.Selection([
        ('available', 'Sẵn sàng'),
        ('maintenance', 'Bảo trì'),
        ('closed', 'Đã đóng'),
    ], string='Trạng thái', default='available', required=True, tracking=True)
    
    # Booking settings
    allow_booking = fields.Boolean(
        string='Cho phép đặt phòng',
        default=True
    )
    booking_advance_days = fields.Integer(
        string='Số ngày đặt trước tối đa',
        default=30,
        help='Số ngày tối đa có thể đặt trước'
    )
    min_booking_duration = fields.Float(
        string='Thời gian đặt tối thiểu (giờ)',
        default=0.5
    )
    max_booking_duration = fields.Float(
        string='Thời gian đặt tối đa (giờ)',
        default=8.0
    )
    
    # Relations
    booking_ids = fields.One2many(
        'dnu.meeting.booking',
        'room_id',
        string='Lịch đặt phòng'
    )
    
    # Computed
    booking_count = fields.Integer(
        compute='_compute_booking_count',
        string='Số lượt đặt'
    )
    is_available_now = fields.Boolean(
        compute='_compute_is_available_now',
        string='Sẵn sàng ngay'
    )
    
    # Additional
    description = fields.Text(string='Mô tả')
    image = fields.Binary(string='Hình ảnh')
    notes = fields.Html(string='Ghi chú')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Người phụ trách',
        tracking=True
    )

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for room in self:
            room.booking_count = len(room.booking_ids)

    @api.depends('state', 'booking_ids')
    def _compute_is_available_now(self):
        """Kiểm tra phòng có sẵn ngay bây giờ không"""
        now = fields.Datetime.now()
        for room in self:
            if room.state != 'available':
                room.is_available_now = False
                continue
            
            # Kiểm tra có booking nào đang diễn ra không
            current_booking = self.env['dnu.meeting.booking'].search([
                ('room_id', '=', room.id),
                ('state', '=', 'confirmed'),
                ('start_datetime', '<=', now),
                ('end_datetime', '>=', now),
            ], limit=1)
            
            room.is_available_now = not bool(current_booking)

    def check_availability(self, start_datetime, end_datetime, exclude_booking_id=None):
        """Kiểm tra phòng có khả dụng trong khoảng thời gian không
        Returns: (available, conflicting_bookings)
        """
        self.ensure_one()
        
        if self.state != 'available':
            return False, []
        
        domain = [
            ('room_id', '=', self.id),
            ('state', '=', 'confirmed'),
            ('start_datetime', '<', end_datetime),
            ('end_datetime', '>', start_datetime),
        ]
        
        if exclude_booking_id:
            domain.append(('id', '!=', exclude_booking_id))
        
        conflicting = self.env['dnu.meeting.booking'].search(domain)
        
        return (len(conflicting) == 0, conflicting)

    def get_available_slots(self, date, duration_hours=1.0):
        """Lấy các khung giờ còn trống trong ngày
        Args:
            date: ngày cần kiểm tra
            duration_hours: thời lượng cần (giờ)
        Returns: list of (start_time, end_time) tuples
        """
        self.ensure_one()
        
        from datetime import datetime, timedelta
        
        # Giờ làm việc: 8h - 18h
        work_start = datetime.combine(date, datetime.min.time().replace(hour=8))
        work_end = datetime.combine(date, datetime.min.time().replace(hour=18))
        
        # Lấy tất cả booking trong ngày
        bookings = self.env['dnu.meeting.booking'].search([
            ('room_id', '=', self.id),
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', work_start),
            ('start_datetime', '<', work_end),
        ], order='start_datetime')
        
        available_slots = []
        current_time = work_start
        duration_delta = timedelta(hours=duration_hours)
        
        for booking in bookings:
            if booking.start_datetime > current_time:
                # Có khoảng trống
                slot_duration = booking.start_datetime - current_time
                if slot_duration >= duration_delta:
                    available_slots.append((current_time, booking.start_datetime))
            current_time = max(current_time, booking.end_datetime)
        
        # Kiểm tra khoảng cuối
        if work_end > current_time:
            if (work_end - current_time) >= duration_delta:
                available_slots.append((current_time, work_end))
        
        return available_slots

    def action_view_bookings(self):
        """Xem lịch đặt phòng"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch đặt phòng',
            'res_model': 'dnu.meeting.booking',
            'view_mode': 'calendar,tree,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã phòng phải là duy nhất!'),
        ('capacity_positive', 'CHECK(capacity >= 0)', 'Sức chứa phải >= 0!'),
    ]
