# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssetAssignment(models.Model):
    _name = 'dnu.asset.assignment'
    _description = 'Lịch sử gán tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(
        string='Mã gán',
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
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên (HR)',
        tracking=True,
        help='Chọn nhân viên từ hệ thống HR'
    )
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        tracking=True,
        help='Chọn nhân viên từ hệ thống Nhân sự'
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        related='employee_id.department_id',
        store=True
    )
    don_vi_id = fields.Many2one(
        'don_vi',
        string='Đơn vị',
        help='Đơn vị công tác của nhân viên'
    )
    
    # Computed để hiển thị tên nhân viên
    employee_name = fields.Char(
        string='Tên nhân viên',
        compute='_compute_employee_name',
        store=True
    )
    
    @api.depends('employee_id', 'nhan_vien_id')
    def _compute_employee_name(self):
        for rec in self:
            if rec.nhan_vien_id:
                rec.employee_name = rec.nhan_vien_id.ho_va_ten
            elif rec.employee_id:
                rec.employee_name = rec.employee_id.name
            else:
                rec.employee_name = False
    
    @api.onchange('nhan_vien_id')
    def _onchange_nhan_vien_id(self):
        """Tự động điền thông tin từ nhân viên"""
        if self.nhan_vien_id and self.nhan_vien_id.hr_employee_id:
            self.employee_id = self.nhan_vien_id.hr_employee_id
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Tự động điền thông tin từ HR employee"""
        if self.employee_id and self.employee_id.nhan_vien_id:
            self.nhan_vien_id = self.employee_id.nhan_vien_id
    date_from = fields.Date(
        string='Từ ngày',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    date_to = fields.Date(
        string='Đến ngày',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Đang sử dụng'),
        ('returned', 'Đã trả'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    notes = fields.Text(string='Ghi chú')
    return_notes = fields.Text(string='Ghi chú khi trả')
    return_condition = fields.Selection([
        ('good', 'Tốt'),
        ('fair', 'Khá'),
        ('poor', 'Kém'),
        ('damaged', 'Hư hỏng'),
    ], string='Tình trạng khi trả')
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.assignment') or _('New')
        
        # Chỉ tự động active khi đã chọn nhân viên (HR hoặc Nhân sự)
        if vals.get('state') == 'draft' and (vals.get('employee_id') or vals.get('nhan_vien_id')):
            vals['state'] = 'active'
        
        assignment = super(AssetAssignment, self).create(vals)
        assignment._update_asset_status()
        return assignment

    def write(self, vals):
        result = super(AssetAssignment, self).write(vals)
        if 'state' in vals or 'date_to' in vals:
            self._update_asset_status()
        return result

    def _update_asset_status(self):
        """Cập nhật trạng thái tài sản khi gán/trả"""
        for assignment in self:
            if assignment.state == 'active':
                asset_updates = {
                    'state': 'assigned',
                    'assignment_date': assignment.date_from,
                }
                # Đồng bộ người được gán từ HR hoặc Nhân sự
                if assignment.employee_id:
                    asset_updates['assigned_to'] = assignment.employee_id.id
                    asset_updates['assigned_nhan_vien_id'] = assignment.employee_id.nhan_vien_id.id if assignment.employee_id.nhan_vien_id else False
                elif assignment.nhan_vien_id:
                    asset_updates['assigned_nhan_vien_id'] = assignment.nhan_vien_id.id
                    asset_updates['assigned_to'] = assignment.nhan_vien_id.hr_employee_id.id if assignment.nhan_vien_id.hr_employee_id else False
                assignment.asset_id.write(asset_updates)
            elif assignment.state == 'returned':
                # Kiểm tra xem có assignment nào khác đang active không
                other_active = self.search([
                    ('asset_id', '=', assignment.asset_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', assignment.id),
                ], limit=1)
                
                if not other_active:
                    assignment.asset_id.write({
                        'state': 'available',
                        'assigned_to': False,
                        'assigned_nhan_vien_id': False,
                        'assignment_date': False,
                    })

    def action_confirm(self):
        """Xác nhận gán tài sản"""
        for assignment in self:
            if not (assignment.employee_id or assignment.nhan_vien_id):
                raise ValidationError(_('Vui lòng chọn nhân viên (HR hoặc Nhân sự) trước khi xác nhận.'))
            if assignment.asset_id.state not in ['available', 'assigned']:
                raise ValidationError(
                    _('Tài sản "%s" không ở trạng thái sẵn sàng để gán!') % assignment.asset_id.name
                )
            assignment.write({'state': 'active'})
            assignment.message_post(
                body=_('Đã gán tài sản cho %s') % (assignment.employee_name or _('(không rõ)'))
            )

    def action_return(self):
        """Trả lại tài sản"""
        for assignment in self:
            assignment.write({
                'state': 'returned',
                'date_to': fields.Date.today(),
            })
            assignment.message_post(
                body=_('Tài sản đã được trả lại')
            )

    def action_cancel(self):
        """Hủy gán tài sản"""
        for assignment in self:
            assignment.write({'state': 'cancelled'})

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Kiểm tra logic ngày"""
        for assignment in self:
            if assignment.date_to and assignment.date_to < assignment.date_from:
                raise ValidationError(_('Ngày kết thúc phải sau ngày bắt đầu!'))

    @api.constrains('asset_id', 'employee_id', 'date_from', 'date_to', 'state')
    def _check_no_overlap(self):
        """Kiểm tra không trùng lặp gán tài sản"""
        for assignment in self:
            if assignment.state not in ['active', 'draft']:
                continue
                
            domain = [
                ('id', '!=', assignment.id),
                ('asset_id', '=', assignment.asset_id.id),
                ('state', '=', 'active'),
            ]
            
            if assignment.date_to:
                domain += [
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>=', assignment.date_from),
                ]
            
            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    _('Tài sản "%s" đã được gán cho nhân viên khác trong khoảng thời gian này!') 
                    % assignment.asset_id.name
                )
