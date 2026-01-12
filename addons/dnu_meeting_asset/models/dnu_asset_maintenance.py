# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssetMaintenance(models.Model):
    _name = 'dnu.asset.maintenance'
    _description = 'Bảo trì tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reported desc'

    name = fields.Char(
        string='Mã bảo trì',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    maintenance_type = fields.Selection([
        ('preventive', 'Bảo trì định kỳ'),
        ('corrective', 'Sửa chữa'),
        ('inspection', 'Kiểm tra'),
    ], string='Loại bảo trì', required=True, default='corrective', tracking=True)
    
    reporter_id = fields.Many2one(
        'hr.employee',
        string='Người báo cáo (HR)',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        help='Chọn từ hệ thống HR'
    )
    nhan_vien_bao_cao_id = fields.Many2one(
        'nhan_vien',
        string='Người báo cáo',
        tracking=True,
        help='Chọn từ hệ thống Nhân sự'
    )
    reporter_name = fields.Char(
        string='Tên người báo cáo',
        compute='_compute_reporter_name',
        store=True
    )
    
    @api.depends('reporter_id', 'nhan_vien_bao_cao_id')
    def _compute_reporter_name(self):
        for rec in self:
            if rec.nhan_vien_bao_cao_id:
                rec.reporter_name = rec.nhan_vien_bao_cao_id.ho_va_ten
            elif rec.reporter_id:
                rec.reporter_name = rec.reporter_id.name
            else:
                rec.reporter_name = False
    
    @api.onchange('nhan_vien_bao_cao_id')
    def _onchange_nhan_vien_bao_cao(self):
        """Tự động liên kết với HR employee nếu có"""
        if self.nhan_vien_bao_cao_id and self.nhan_vien_bao_cao_id.hr_employee_id:
            self.reporter_id = self.nhan_vien_bao_cao_id.hr_employee_id
    
    @api.onchange('reporter_id')
    def _onchange_reporter(self):
        """Tự động liên kết với nhân viên nếu có"""
        if self.reporter_id and self.reporter_id.nhan_vien_id:
            self.nhan_vien_bao_cao_id = self.reporter_id.nhan_vien_id
    
    date_reported = fields.Datetime(
        string='Ngày báo cáo',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    description = fields.Text(
        string='Mô tả sự cố',
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Chờ xử lý'),
        ('in_progress', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    priority = fields.Selection([
        ('low', 'Thấp'),
        ('normal', 'Bình thường'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp'),
    ], string='Độ ưu tiên', default='normal', tracking=True)
    
    assigned_tech_id = fields.Many2one(
        'hr.employee',
        string='Kỹ thuật viên (HR)',
        tracking=True,
        help='Chọn kỹ thuật viên từ hệ thống HR'
    )
    nhan_vien_ky_thuat_id = fields.Many2one(
        'nhan_vien',
        string='Kỹ thuật viên',
        tracking=True,
        help='Chọn kỹ thuật viên từ hệ thống Nhân sự'
    )
    tech_name = fields.Char(
        string='Tên kỹ thuật viên',
        compute='_compute_tech_name',
        store=True
    )
    
    @api.depends('assigned_tech_id', 'nhan_vien_ky_thuat_id')
    def _compute_tech_name(self):
        for rec in self:
            if rec.nhan_vien_ky_thuat_id:
                rec.tech_name = rec.nhan_vien_ky_thuat_id.ho_va_ten
            elif rec.assigned_tech_id:
                rec.tech_name = rec.assigned_tech_id.name
            else:
                rec.tech_name = False
    
    @api.onchange('nhan_vien_ky_thuat_id')
    def _onchange_nhan_vien_ky_thuat(self):
        """Tự động liên kết với HR employee nếu có"""
        if self.nhan_vien_ky_thuat_id and self.nhan_vien_ky_thuat_id.hr_employee_id:
            self.assigned_tech_id = self.nhan_vien_ky_thuat_id.hr_employee_id
    
    @api.onchange('assigned_tech_id')
    def _onchange_assigned_tech(self):
        """Tự động liên kết với nhân viên nếu có"""
        if self.assigned_tech_id and self.assigned_tech_id.nhan_vien_id:
            self.nhan_vien_ky_thuat_id = self.assigned_tech_id.nhan_vien_id
    
    date_scheduled = fields.Datetime(
        string='Ngày hẹn',
        tracking=True
    )
    date_started = fields.Datetime(
        string='Ngày bắt đầu',
        tracking=True
    )
    date_completed = fields.Datetime(
        string='Ngày hoàn thành',
        tracking=True
    )
    
    # Cost information
    cost_estimate = fields.Float(
        string='Chi phí dự kiến',
        tracking=True
    )
    cost_actual = fields.Float(
        string='Chi phí thực tế',
        tracking=True
    )
    
    work_done = fields.Text(string='Công việc đã làm')
    parts_used = fields.Text(string='Vật tư sử dụng')
    notes = fields.Html(string='Ghi chú')
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu đính kèm'
    )
    
    # Liên kết với lịch bảo trì định kỳ
    schedule_id = fields.Many2one(
        'dnu.maintenance.schedule',
        string='Lịch bảo trì định kỳ',
        help='Nếu phiếu này được tạo từ lịch bảo trì định kỳ'
    )
    
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    # Computed
    duration_days = fields.Float(
        string='Thời gian xử lý (ngày)',
        compute='_compute_duration',
        store=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.maintenance') or _('New')
        
        maintenance = super(AssetMaintenance, self).create(vals)
        
        # Auto chuyển sang pending
        if vals.get('state') == 'draft':
            maintenance.action_submit()
        
        return maintenance

    @api.depends('date_started', 'date_completed')
    def _compute_duration(self):
        for maintenance in self:
            if maintenance.date_started and maintenance.date_completed:
                delta = maintenance.date_completed - maintenance.date_started
                maintenance.duration_days = delta.days + (delta.seconds / 86400.0)
            else:
                maintenance.duration_days = 0.0

    def action_submit(self):
        """Gửi yêu cầu bảo trì"""
        for maintenance in self:
            maintenance.write({'state': 'pending'})
            # Tự động set asset sang maintenance state
            if maintenance.priority in ['high', 'urgent']:
                maintenance.asset_id.write({'state': 'maintenance'})
            
            maintenance.message_post(
                body=_('Yêu cầu bảo trì đã được gửi')
            )

    def action_start(self):
        """Bắt đầu xử lý"""
        for maintenance in self:
            if not maintenance.assigned_tech_id:
                raise ValidationError(_('Vui lòng chọn kỹ thuật viên!'))
            
            maintenance.write({
                'state': 'in_progress',
                'date_started': fields.Datetime.now(),
            })
            maintenance.asset_id.write({'state': 'maintenance'})

    def action_done(self):
        """Hoàn thành bảo trì"""
        for maintenance in self:
            maintenance.write({
                'state': 'done',
                'date_completed': fields.Datetime.now(),
            })
            
            # Trả asset về available nếu không có maintenance nào khác đang active
            other_maintenance = self.search([
                ('asset_id', '=', maintenance.asset_id.id),
                ('state', 'in', ['pending', 'in_progress']),
                ('id', '!=', maintenance.id),
            ], limit=1)
            
            if not other_maintenance:
                maintenance.asset_id.write({'state': 'available'})

    def action_cancel(self):
        """Hủy bảo trì"""
        for maintenance in self:
            maintenance.write({'state': 'cancelled'})

    @api.constrains('date_scheduled', 'date_started', 'date_completed')
    def _check_dates(self):
        """Kiểm tra logic ngày"""
        for maintenance in self:
            if maintenance.date_started and maintenance.date_completed:
                if maintenance.date_completed < maintenance.date_started:
                    raise ValidationError(_('Ngày hoàn thành phải sau ngày bắt đầu!'))
