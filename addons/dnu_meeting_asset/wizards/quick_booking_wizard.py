# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, datetime
import pytz


class QuickBookingWizard(models.TransientModel):
    """Wizard đặt phòng nhanh với gợi ý phòng phù hợp"""
    _name = 'dnu.quick.booking.wizard'
    _description = 'Đặt phòng nhanh'

    # Thông tin cuộc họp
    subject = fields.Char(
        string='Chủ đề cuộc họp',
        required=True
    )
    description = fields.Html(string='Mô tả')
    
    # Thời gian
    date = fields.Date(
        string='Ngày họp',
        required=True,
        default=fields.Date.today
    )
    start_time = fields.Float(
        string='Giờ bắt đầu',
        required=True,
        default=9.0,
        help='Định dạng: 9.5 = 9:30'
    )
    duration = fields.Float(
        string='Thời lượng (giờ)',
        required=True,
        default=1.0
    )
    
    # Computed datetime
    start_datetime = fields.Datetime(
        compute='_compute_datetimes',
        string='Thời gian bắt đầu'
    )
    end_datetime = fields.Datetime(
        compute='_compute_datetimes',
        string='Thời gian kết thúc'
    )
    
    # Yêu cầu
    num_attendees = fields.Integer(
        string='Số người tham dự',
        required=True,
        default=5
    )
    organizer_id = fields.Many2one(
        'hr.employee',
        string='Người tổ chức',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    attendee_ids = fields.Many2many(
        'hr.employee',
        string='Người tham dự'
    )
    
    # Tiện nghi yêu cầu
    need_projector = fields.Boolean(string='Cần máy chiếu')
    need_video_conference = fields.Boolean(string='Cần hệ thống họp trực tuyến')
    need_whiteboard = fields.Boolean(string='Cần bảng trắng')
    
    # Thiết bị bổ sung
    required_equipment_ids = fields.Many2many(
        'dnu.asset',
        string='Thiết bị bổ sung',
        domain=[('state', '=', 'available')]
    )
    
    # Kết quả gợi ý
    suggested_room_ids = fields.Many2many(
        'dnu.meeting.room',
        compute='_compute_suggested_rooms',
        string='Phòng gợi ý'
    )
    selected_room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng được chọn'
    )
    
    # Thông báo
    message = fields.Html(
        compute='_compute_suggested_rooms',
        string='Thông báo'
    )

    @api.depends('date', 'start_time', 'duration')
    def _compute_datetimes(self):
        for wizard in self:
            if wizard.date and wizard.start_time:
                # Chuyển đổi giờ float sang time
                hours = int(wizard.start_time)
                minutes = int((wizard.start_time - hours) * 60)
                
                # Tạo datetime local (naive)
                start_dt = datetime.combine(
                    wizard.date,
                    datetime.min.time().replace(hour=hours, minute=minutes)
                )
                
                # Lấy timezone của user, mặc định là Asia/Ho_Chi_Minh
                tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Ho_Chi_Minh'
                user_tz = pytz.timezone(tz_name)
                
                # Localize datetime với timezone của user, sau đó convert sang UTC
                start_dt_local = user_tz.localize(start_dt)
                start_dt_utc = start_dt_local.astimezone(pytz.UTC)
                
                # Lưu dưới dạng naive UTC (Odoo yêu cầu)
                wizard.start_datetime = start_dt_utc.replace(tzinfo=None)
                wizard.end_datetime = wizard.start_datetime + timedelta(hours=wizard.duration)
            else:
                wizard.start_datetime = False
                wizard.end_datetime = False

    @api.depends('date', 'start_time', 'duration', 'num_attendees', 
                 'need_projector', 'need_video_conference', 'need_whiteboard')
    def _compute_suggested_rooms(self):
        for wizard in self:
            if not wizard.start_datetime or not wizard.end_datetime:
                wizard.suggested_room_ids = False
                wizard.message = '<p class="text-muted">Vui lòng chọn ngày và giờ họp</p>'
                continue
            
            # Tìm phòng phù hợp
            domain = [
                ('state', '=', 'available'),
                ('allow_booking', '=', True),
                ('capacity', '>=', wizard.num_attendees),
            ]
            
            # Thêm điều kiện tiện nghi
            if wizard.need_projector:
                domain.append(('has_projector', '=', True))
            if wizard.need_video_conference:
                domain.append(('has_video_conference', '=', True))
            if wizard.need_whiteboard:
                domain.append(('has_whiteboard', '=', True))
            
            rooms = self.env['dnu.meeting.room'].search(domain, order='capacity')
            
            # Lọc phòng còn trống trong khoảng thời gian
            available_rooms = self.env['dnu.meeting.room']
            for room in rooms:
                available, _ = room.check_availability(
                    wizard.start_datetime,
                    wizard.end_datetime
                )
                if available:
                    # Kiểm tra thời lượng min/max
                    if room.min_booking_duration <= wizard.duration <= room.max_booking_duration:
                        available_rooms |= room
            
            wizard.suggested_room_ids = available_rooms
            
            if available_rooms:
                wizard.message = '<p class="text-success"><i class="fa fa-check"></i> Tìm thấy %d phòng phù hợp</p>' % len(available_rooms)
            else:
                wizard.message = '<p class="text-warning"><i class="fa fa-exclamation-triangle"></i> Không tìm thấy phòng phù hợp. Vui lòng thử thời gian khác hoặc giảm yêu cầu.</p>'

    @api.onchange('suggested_room_ids')
    def _onchange_suggested_rooms(self):
        """Tự động chọn phòng đầu tiên nếu có"""
        if self.suggested_room_ids and not self.selected_room_id:
            self.selected_room_id = self.suggested_room_ids[0]

    def action_book(self):
        """Tạo đặt phòng"""
        self.ensure_one()
        
        if not self.selected_room_id:
            raise UserError(_('Vui lòng chọn phòng họp!'))
        
        # Kiểm tra lại tính khả dụng
        available, conflicts = self.selected_room_id.check_availability(
            self.start_datetime,
            self.end_datetime
        )
        
        if not available:
            raise UserError(_('Phòng "%s" đã bị đặt trong khoảng thời gian này!') % self.selected_room_id.name)
        
        # Tạo booking
        booking = self.env['dnu.meeting.booking'].create({
            'subject': self.subject,
            'description': self.description,
            'room_id': self.selected_room_id.id,
            'organizer_id': self.organizer_id.id,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'attendee_ids': [(6, 0, self.attendee_ids.ids)],
            'required_equipment_ids': [(6, 0, self.required_equipment_ids.ids)],
            'external_attendees': max(0, self.num_attendees - len(self.attendee_ids) - 1),
            'state': 'draft',
        })
        
        # Tự động submit
        booking.action_submit()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đặt phòng mới',
            'res_model': 'dnu.meeting.booking',
            'res_id': booking.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_calendar(self):
        """Xem lịch phòng họp"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch phòng họp',
            'res_model': 'dnu.meeting.booking',
            'view_mode': 'calendar,tree',
            'domain': [('start_datetime', '>=', self.start_datetime.date().strftime('%Y-%m-%d'))] if self.start_datetime else [],
            'context': {'search_default_confirmed': 1},
        }


class AssetReturnWizard(models.TransientModel):
    """Wizard trả tài sản mượn"""
    _name = 'dnu.asset.return.wizard'
    _description = 'Trả tài sản mượn'

    lending_id = fields.Many2one(
        'dnu.asset.lending',
        string='Phiếu mượn',
        required=True
    )
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        related='lending_id.asset_id',
        readonly=True
    )
    borrower_id = fields.Many2one(
        'hr.employee',
        string='Người mượn',
        related='lending_id.borrower_id',
        readonly=True
    )
    
    return_condition = fields.Selection([
        ('good', 'Tốt - Như cũ'),
        ('normal', 'Bình thường'),
        ('damaged', 'Hư hỏng nhẹ'),
        ('broken', 'Hỏng nặng'),
    ], string='Tình trạng khi trả', required=True, default='good')
    
    return_notes = fields.Text(string='Ghi chú')
    create_maintenance = fields.Boolean(
        string='Tạo yêu cầu bảo trì',
        compute='_compute_create_maintenance',
        store=True,
        readonly=False
    )
    maintenance_description = fields.Text(string='Mô tả hư hỏng')

    @api.depends('return_condition')
    def _compute_create_maintenance(self):
        for wizard in self:
            wizard.create_maintenance = wizard.return_condition in ['damaged', 'broken']

    def action_return(self):
        """Xác nhận trả tài sản"""
        self.ensure_one()
        
        self.lending_id.write({
            'return_condition': self.return_condition,
            'return_notes': self.return_notes,
        })
        
        self.lending_id.action_return()
        
        # Tạo yêu cầu bảo trì nếu cần
        if self.create_maintenance and self.maintenance_description:
            self.env['dnu.asset.maintenance'].create({
                'asset_id': self.asset_id.id,
                'maintenance_type': 'corrective',
                'reporter_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'description': self.maintenance_description,
                'priority': 'high' if self.return_condition == 'broken' else 'normal',
                'state': 'pending',
            })
        
        return {'type': 'ir.actions.act_window_close'}
