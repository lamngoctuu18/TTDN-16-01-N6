# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class MaintenanceSchedule(models.Model):
    """Quản lý lịch bảo trì định kỳ"""
    _name = 'dnu.maintenance.schedule'
    _description = 'Lịch bảo trì định kỳ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_date'

    name = fields.Char(
        string='Tên lịch bảo trì',
        required=True,
        tracking=True
    )
    
    # Loại đối tượng
    target_type = fields.Selection([
        ('asset', 'Tài sản'),
        ('room', 'Phòng họp'),
    ], string='Loại đối tượng', required=True, default='asset', tracking=True)
    
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        tracking=True
    )
    room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng họp',
        tracking=True
    )
    
    # Tần suất bảo trì
    frequency_type = fields.Selection([
        ('days', 'Ngày'),
        ('weeks', 'Tuần'),
        ('months', 'Tháng'),
        ('years', 'Năm'),
    ], string='Đơn vị', required=True, default='months', tracking=True)
    frequency_interval = fields.Integer(
        string='Tần suất',
        required=True,
        default=1,
        help='Ví dụ: 3 tháng một lần'
    )
    
    # Lịch trình
    start_date = fields.Date(
        string='Ngày bắt đầu',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    next_date = fields.Date(
        string='Lần bảo trì tiếp theo',
        compute='_compute_next_date',
        store=True,
        tracking=True
    )
    last_maintenance_date = fields.Date(
        string='Lần bảo trì gần nhất',
        readonly=True
    )
    last_maintenance_id = fields.Many2one(
        'dnu.asset.maintenance',
        string='Phiếu bảo trì gần nhất',
        readonly=True
    )
    
    # Thông tin bảo trì
    maintenance_type = fields.Selection([
        ('preventive', 'Bảo trì định kỳ'),
        ('inspection', 'Kiểm tra'),
    ], string='Loại bảo trì', required=True, default='preventive')
    description = fields.Text(
        string='Mô tả công việc bảo trì',
        required=True
    )
    estimated_duration = fields.Float(
        string='Thời gian ước tính (giờ)',
        default=1.0
    )
    assigned_tech_id = fields.Many2one(
        'hr.employee',
        string='Kỹ thuật viên phụ trách'
    )
    
    # Cài đặt
    advance_days = fields.Integer(
        string='Tạo trước (ngày)',
        default=7,
        help='Số ngày tạo phiếu bảo trì trước ngày dự kiến'
    )
    send_reminder = fields.Boolean(
        string='Gửi nhắc nhở',
        default=True
    )
    
    state = fields.Selection([
        ('active', 'Hoạt động'),
        ('paused', 'Tạm dừng'),
        ('stopped', 'Dừng'),
    ], string='Trạng thái', default='active', required=True, tracking=True)
    
    notes = fields.Text(string='Ghi chú')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    # Lịch sử
    maintenance_count = fields.Integer(
        compute='_compute_maintenance_count',
        string='Số lần bảo trì'
    )
    maintenance_ids = fields.One2many(
        'dnu.asset.maintenance',
        'schedule_id',
        string='Lịch sử bảo trì'
    )

    @api.constrains('target_type', 'asset_id', 'room_id')
    def _check_target(self):
        for schedule in self:
            if schedule.target_type == 'asset' and not schedule.asset_id:
                raise ValidationError(_('Vui lòng chọn tài sản!'))
            if schedule.target_type == 'room' and not schedule.room_id:
                raise ValidationError(_('Vui lòng chọn phòng họp!'))

    @api.depends('start_date', 'frequency_type', 'frequency_interval', 'last_maintenance_date')
    def _compute_next_date(self):
        for schedule in self:
            base_date = schedule.last_maintenance_date or schedule.start_date
            if not base_date:
                schedule.next_date = False
                continue
            
            if schedule.frequency_type == 'days':
                schedule.next_date = base_date + timedelta(days=schedule.frequency_interval)
            elif schedule.frequency_type == 'weeks':
                schedule.next_date = base_date + timedelta(weeks=schedule.frequency_interval)
            elif schedule.frequency_type == 'months':
                schedule.next_date = base_date + relativedelta(months=schedule.frequency_interval)
            elif schedule.frequency_type == 'years':
                schedule.next_date = base_date + relativedelta(years=schedule.frequency_interval)

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for schedule in self:
            schedule.maintenance_count = len(schedule.maintenance_ids)

    @api.onchange('target_type')
    def _onchange_target_type(self):
        if self.target_type == 'asset':
            self.room_id = False
        else:
            self.asset_id = False

    def action_pause(self):
        """Tạm dừng lịch bảo trì"""
        self.write({'state': 'paused'})

    def action_resume(self):
        """Tiếp tục lịch bảo trì"""
        self.write({'state': 'active'})

    def action_stop(self):
        """Dừng lịch bảo trì"""
        self.write({'state': 'stopped'})

    def action_create_maintenance(self):
        """Tạo phiếu bảo trì thủ công"""
        self.ensure_one()
        return self._create_maintenance_request()

    def action_view_maintenances(self):
        """Xem lịch sử bảo trì"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử bảo trì',
            'res_model': 'dnu.asset.maintenance',
            'view_mode': 'tree,form',
            'domain': [('schedule_id', '=', self.id)],
            'context': {'default_schedule_id': self.id},
        }

    def _create_maintenance_request(self):
        """Tạo phiếu bảo trì từ lịch định kỳ"""
        self.ensure_one()
        
        vals = {
            'asset_id': self.asset_id.id if self.target_type == 'asset' else False,
            'maintenance_type': self.maintenance_type,
            'description': self.description,
            'assigned_tech_id': self.assigned_tech_id.id if self.assigned_tech_id else False,
            'date_scheduled': fields.Datetime.now(),
            'schedule_id': self.id,
            'state': 'pending',
        }
        
        maintenance = self.env['dnu.asset.maintenance'].create(vals)
        
        # Cập nhật lịch
        self.write({
            'last_maintenance_date': fields.Date.today(),
            'last_maintenance_id': maintenance.id,
        })
        
        return maintenance

    @api.model
    def _cron_generate_scheduled_maintenance(self):
        """Cron job tạo phiếu bảo trì định kỳ"""
        today = fields.Date.today()
        
        # Tìm các lịch bảo trì cần tạo phiếu
        schedules = self.search([
            ('state', '=', 'active'),
            ('next_date', '<=', today + timedelta(days=7)),  # Tạo trước 7 ngày
        ])
        
        for schedule in schedules:
            # Kiểm tra xem đã có phiếu bảo trì chờ xử lý chưa
            pending = self.env['dnu.asset.maintenance'].search([
                ('schedule_id', '=', schedule.id),
                ('state', 'in', ['draft', 'pending', 'in_progress']),
            ], limit=1)
            
            if not pending:
                schedule._create_maintenance_request()
                
                # Gửi nhắc nhở
                if schedule.send_reminder:
                    schedule.message_post(
                        body=_('Đã tạo phiếu bảo trì định kỳ cho %s') % (
                            schedule.asset_id.name if schedule.target_type == 'asset' 
                            else schedule.room_id.name
                        )
                    )
