# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import secrets
import string


class EventMeetingRoom(models.Model):
    _name = 'event.meeting.room'
    _description = 'Event Meeting Room'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.published.mixin']
    _order = 'is_pinned desc, last_activity_date desc, create_date desc'

    # Basic Info
    name = fields.Char(
        string='Tên Phòng',
        required=True,
        tracking=True,
        translate=True,
        help='Chủ đề hoặc nội dung của phòng họp'
    )
    summary = fields.Text(
        string='Tóm Tắt',
        translate=True,
        help='Mô tả ngắn gọn về mục đích của phòng'
    )
    description = fields.Html(
        string='Mô Tả',
        translate=True,
        sanitize_attributes=False,
        sanitize_form=False,
    )
    
    # Event relation
    event_id = fields.Many2one(
        'event.event',
        string='Sự Kiện',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    event_date_begin = fields.Datetime(related='event_id.date_begin', store=True)
    event_date_end = fields.Datetime(related='event_id.date_end', store=True)
    
    # Creator
    create_uid = fields.Many2one(
        'res.users',
        string='Người Tạo',
        readonly=True,
        index=True
    )
    creator_name = fields.Char(
        string='Tên Người Tạo',
        compute='_compute_creator_name',
        store=True
    )
    
    # Language
    language_id = fields.Many2one(
        'res.lang',
        string='Ngôn Ngữ',
        help='Ngôn ngữ chính được sử dụng trong phòng này'
    )
    language_code = fields.Char(related='language_id.code', store=True)
    
    # Capacity
    max_capacity = fields.Integer(
        string='Sức Chứa Tối Đa',
        default=50,
        required=True,
        help='Số lượng người tham gia tối đa'
    )
    current_participants = fields.Integer(
        string='Số Người Hiện Tại',
        default=0,
        help='Số người hiện đang ở trong phòng'
    )
    is_full = fields.Boolean(
        string='Phòng Đầy',
        compute='_compute_is_full',
        store=True
    )
    
    # Target audience
    target_audience = fields.Selection([
        ('all', 'Mọi Người'),
        ('beginners', 'Người Mới Bắt Đầu'),
        ('intermediate', 'Trung Cấp'),
        ('advanced', 'Nâng Cao'),
        ('speakers', 'Chỉ Diễn Giả'),
        ('sponsors', 'Nhà Tài Trợ'),
        ('vip', 'VIP'),
    ], string='Đối Tượng Mục Tiêu', default='all')
    
    # Status
    is_pinned = fields.Boolean(
        string='Đã Ghim',
        default=False,
        tracking=True,
        help='Phòng đã ghim xuất hiện đầu tiên và không tự động lưu trữ'
    )
    is_closed = fields.Boolean(
        string='Đã Đóng',
        default=False,
        tracking=True,
        help='Phòng đã đóng không thể nhận thêm người tham gia'
    )
    active = fields.Boolean(
        string='Hoạt Động',
        default=True,
        help='Phòng không hoạt động sẽ bị lưu trữ'
    )
    
    # Activity tracking
    last_activity_date = fields.Datetime(
        string='Hoạt Động Gần Nhất',
        default=fields.Datetime.now,
        help='Lần cuối cùng có người tham gia hoặc hoạt động trong phòng'
    )
    total_visits = fields.Integer(
        string='Tổng Lượt Truy Cập',
        default=0,
        help='Tổng số lần mọi người tham gia phòng này'
    )
    
    # Jitsi integration
    room_token = fields.Char(
        string='Mã Phòng',
        copy=False,
        index=True,
        readonly=True,
        help='Mã định danh duy nhất cho URL phòng'
    )
    jitsi_room_name = fields.Char(
        string='Tên Phòng Jitsi',
        compute='_compute_jitsi_room_name',
        store=True
    )
    room_url = fields.Char(
        string='URL Phòng',
        compute='_compute_room_url',
        help='URL đầy đủ để truy cập phòng này'
    )
    
    # Website
    website_url = fields.Char(
        string='URL Website',
        compute='_compute_website_url',
        help='URL công khai đến trang phòng'
    )

    @api.depends('create_uid', 'create_uid.name')
    def _compute_creator_name(self):
        for room in self:
            room.creator_name = room.create_uid.name if room.create_uid else 'Unknown'

    @api.depends('current_participants', 'max_capacity')
    def _compute_is_full(self):
        for room in self:
            room.is_full = room.current_participants >= room.max_capacity

    @api.depends('event_id', 'room_token')
    def _compute_jitsi_room_name(self):
        """Generate Jitsi room name"""
        for room in self:
            if room.event_id and room.room_token:
                # Format: event-slug_room-token
                event_slug = room.event_id.name.lower().replace(' ', '-')[:30]
                room.jitsi_room_name = f"{event_slug}_{room.room_token}"
            else:
                room.jitsi_room_name = False

    @api.depends('jitsi_room_name')
    def _compute_room_url(self):
        """Generate Jitsi meeting URL"""
        jitsi_server = self.env['ir.config_parameter'].sudo().get_param(
            'website_jitsi.jitsi_server_domain',
            'meet.jit.si'
        )
        for room in self:
            if room.jitsi_room_name:
                room.room_url = f"https://{jitsi_server}/{room.jitsi_room_name}"
            else:
                room.room_url = False

    @api.depends('event_id', 'room_token')
    def _compute_website_url(self):
        """Generate public website URL"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for room in self:
            if room.event_id and room.room_token:
                room.website_url = f"{base_url}/event/{room.event_id.id}/room/{room.room_token}"
            else:
                room.website_url = False

    @api.model_create_multi
    def create(self, vals_list):
        """Generate room token on create"""
        for vals in vals_list:
            if not vals.get('room_token'):
                vals['room_token'] = self._generate_room_token()
        return super().create(vals_list)

    def _generate_room_token(self):
        """Generate unique random token"""
        chars = string.ascii_lowercase + string.digits
        while True:
            token = ''.join(secrets.choice(chars) for _ in range(12))
            if not self.search([('room_token', '=', token)], limit=1):
                return token

    def write(self, vals):
        """Track activity when room is accessed"""
        if 'current_participants' in vals:
            vals['last_activity_date'] = fields.Datetime.now()
        return super().write(vals)

    @api.constrains('max_capacity')
    def _check_max_capacity(self):
        for room in self:
            if room.max_capacity < 1:
                raise ValidationError(_('Sức chứa phòng phải ít nhất là 1'))
            if room.max_capacity > 1000:
                raise ValidationError(_('Sức chứa phòng không được vượt quá 1000'))

    def action_pin(self):
        """Pin this room"""
        self.ensure_one()
        self.is_pinned = True
        self.message_post(body=_('Phòng đã được ghim'))

    def action_unpin(self):
        """Unpin this room"""
        self.ensure_one()
        self.is_pinned = False
        self.message_post(body=_('Phòng đã được bỏ ghim'))

    def action_close(self):
        """Close this room"""
        self.ensure_one()
        self.is_closed = True
        self.message_post(body=_('Phòng đã được đóng'))

    def action_reopen(self):
        """Reopen this room"""
        self.ensure_one()
        if self.is_full:
            raise UserError(_('Không thể mở lại phòng đã đầy'))
        self.is_closed = False
        self.message_post(body=_('Phòng đã được mở lại'))

    def action_duplicate_room(self):
        """Duplicate this room"""
        self.ensure_one()
        new_room = self.copy({
            'name': _('%s (Bản sao)') % self.name,
            'current_participants': 0,
            'is_pinned': False,
            'is_closed': False,
            'total_visits': 0,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.meeting.room',
            'res_id': new_room.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def join_room(self):
        """Increment participant count"""
        self.ensure_one()
        if self.is_closed:
            raise UserError(_('Phòng này đã đóng'))
        if self.is_full:
            raise UserError(_('Phòng này đã đầy'))
        
        self.write({
            'current_participants': self.current_participants + 1,
            'total_visits': self.total_visits + 1,
            'last_activity_date': fields.Datetime.now(),
        })

    def leave_room(self):
        """Decrement participant count"""
        self.ensure_one()
        if self.current_participants > 0:
            self.current_participants -= 1

    @api.model
    def _cron_archive_inactive_rooms(self):
        """Archive rooms inactive for X hours (excluding pinned)"""
        for event_type in self.env['event.type'].search([('allow_community', '=', True)]):
            archive_hours = event_type.room_auto_archive_hours or 4
            cutoff_time = datetime.now() - timedelta(hours=archive_hours)
            
            inactive_rooms = self.search([
                ('event_id.event_type_id', '=', event_type.id),
                ('is_pinned', '=', False),
                ('active', '=', True),
                ('last_activity_date', '<', cutoff_time),
            ])
            
            if inactive_rooms:
                inactive_rooms.write({'active': False})
                self.env.cr.commit()
