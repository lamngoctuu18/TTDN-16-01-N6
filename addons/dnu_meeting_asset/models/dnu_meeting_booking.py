# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


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
        tracking=True
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
        if self.nhan_vien_to_chuc_id and self.nhan_vien_to_chuc_id.hr_employee_id:
            self.organizer_id = self.nhan_vien_to_chuc_id.hr_employee_id
    
    @api.onchange('organizer_id')
    def _onchange_organizer(self):
        """Tự động liên kết với nhân viên nếu có"""
        if self.organizer_id and self.organizer_id.nhan_vien_id:
            self.nhan_vien_to_chuc_id = self.organizer_id.nhan_vien_id
    
    attendee_ids = fields.Many2many(
        'hr.employee',
        'booking_attendee_rel',
        'booking_id',
        'employee_id',
        string='Người tham dự'
    )
    num_attendees = fields.Integer(
        string='Số người dự kiến',
        compute='_compute_num_attendees',
        store=True,
        help='Tổng số người tham dự (bao gồm người tổ chức)'
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
        string='Thiết bị yêu cầu',
        domain=[('state', 'in', ['available', 'assigned'])]
    )
    
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
        
        # Tự động tạo calendar event nếu cần
        if booking.state == 'confirmed':
            booking._create_calendar_event()
        
        return booking

    def write(self, vals):
        result = super(MeetingBooking, self).write(vals)
        
        # Cập nhật calendar event
        if any(key in vals for key in ['start_datetime', 'end_datetime', 'subject', 'room_id']):
            for booking in self:
                if booking.calendar_event_id:
                    booking._update_calendar_event()
        
        return result

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for booking in self:
            if booking.start_datetime and booking.end_datetime:
                delta = booking.end_datetime - booking.start_datetime
                booking.duration = delta.total_seconds() / 3600.0
            else:
                booking.duration = 0.0

    @api.depends('attendee_ids', 'organizer_id')
    def _compute_num_attendees(self):
        for booking in self:
            attendees = len(booking.attendee_ids)
            # Thêm người tổ chức nếu chưa có trong danh sách
            if booking.organizer_id and booking.organizer_id not in booking.attendee_ids:
                attendees += 1
            booking.num_attendees = attendees + booking.external_attendees

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
        """Gửi yêu cầu đặt phòng"""
        for booking in self:
            booking.write({'state': 'submitted'})
            booking.message_post(body=_('Yêu cầu đặt phòng đã được gửi'))

    def action_confirm(self):
        """Xác nhận đặt phòng"""
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
            booking._send_confirmation_email()
            booking.message_post(body=_('Đặt phòng đã được xác nhận'))
        
        # Thông báo và chuyển về calendar
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã duyệt %s lịch đặt phòng. Xem trong lịch bằng cách bỏ filter hoặc chuyển đến ngày đặt.') % len(self),
                'type': 'success',
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

    def _send_confirmation_email(self):
        """Gửi email xác nhận"""
        template = self.env.ref('dnu_meeting_asset.email_template_booking_confirmation', raise_if_not_found=False)
        if template:
            for booking in self:
                template.send_mail(booking.id, force_send=True)

    def _send_cancellation_email(self):
        """Gửi email thông báo hủy"""
        template = self.env.ref('dnu_meeting_asset.email_template_booking_cancellation', raise_if_not_found=False)
        if template:
            for booking in self:
                template.send_mail(booking.id, force_send=True)

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
