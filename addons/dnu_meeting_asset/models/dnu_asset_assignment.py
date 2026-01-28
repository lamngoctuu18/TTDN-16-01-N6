# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


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
        default=lambda self: self._get_default_nhan_vien(),
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
    
    def _get_default_nhan_vien(self):
        """Tìm nhân viên có chức vụ Kiểm kê thuộc đơn vị Bảo Trì"""
        # Tìm đơn vị Bảo Trì
        don_vi_bao_tri = self.env['don_vi'].search([
            '|', ('ten_don_vi', 'ilike', 'Bảo Trì'),
            ('ten_don_vi', 'ilike', 'Bảo trì')
        ], limit=1)
        
        if not don_vi_bao_tri:
            return False
        
        # Tìm chức vụ Kiểm kê
        chuc_vu_kiem_ke = self.env['chuc_vu'].search([
            '|', ('ten_chuc_vu', 'ilike', 'Kiểm kê'),
            ('ten_chuc_vu', 'ilike', 'Kiểm Kê')
        ], limit=1)
        
        if not chuc_vu_kiem_ke:
            return False
        
        # Tìm nhân viên có chức vụ Kiểm kê và thuộc đơn vị Bảo Trì
        nhan_vien = self.env['nhan_vien'].search([
            ('don_vi_chinh_id', '=', don_vi_bao_tri.id),
            ('chuc_vu_chinh_id', '=', chuc_vu_kiem_ke.id)
        ], limit=1)
        
        return nhan_vien.id if nhan_vien else False
    
    @api.onchange('nhan_vien_id')
    def _onchange_nhan_vien_id(self):
        """Tự động điền thông tin từ nhân viên"""
        if self.nhan_vien_id:
            # Tự động điền đơn vị từ don_vi_chinh_id
            if self.nhan_vien_id.don_vi_chinh_id:
                self.don_vi_id = self.nhan_vien_id.don_vi_chinh_id
            # Tự động điền HR employee nếu có
            if self.nhan_vien_id.hr_employee_id:
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
    
    # Biên bản bàn giao
    handover_id = fields.Many2one(
        'dnu.asset.handover',
        string='Biên bản bàn giao',
        help='Biên bản bàn giao khi gán tài sản'
    )
    handover_state = fields.Selection(
        related='handover_id.state',
        string='Trạng thái biên bản',
        readonly=True,
        store=False
    )
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    van_ban_den_count = fields.Integer(
        string='Văn bản đến',
        compute='_compute_van_ban_den_count',
        store=False
    )

    def _compute_van_ban_den_count(self):
        VanBanDen = self.env['van_ban_den']
        for rec in self:
            rec.van_ban_den_count = VanBanDen.search_count([
                ('source_model', '=', rec._name),
                ('source_res_id', '=', rec.id),
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

    def action_create_van_ban_den(self):
        self.ensure_one()
        department = self.don_vi_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo văn bản đến',
            'res_model': 'van_ban_den',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_source_model': self._name,
                'default_source_res_id': self.id,
                'default_ten_van_ban': f'Văn bản đến - Gán tài sản {self.name}',
                'default_department_id': department.id if department else False,
                'default_due_date': fields.Date.to_string(self.date_from) if self.date_from else False,
            },
        }

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

            # Kiểm tra biên bản bàn giao nếu có
            if assignment.handover_id:
                if assignment.handover_id.state != 'completed':
                    raise UserError(_('Biên bản bàn giao phải được ký và Hoàn thành trước khi xác nhận gán.'))

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
    
    def action_create_handover(self):
        """Tạo biên bản bàn giao"""
        self.ensure_one()
        
        if self.handover_id:
            raise UserError(_('Biên bản bàn giao đã được tạo!'))
        
        receiver = self.nhan_vien_id or (self.employee_id.nhan_vien_id if self.employee_id else False)
        if not receiver:
            raise UserError(_('Vui lòng chọn Nhân viên (Nhân sự) để tạo biên bản.'))
        
        # Tìm người đang được gán tài sản hiện tại làm người giao
        current_holder = False
        if self.asset_id.assigned_nhan_vien_id:
            current_holder = self.asset_id.assigned_nhan_vien_id
        else:
            # Tìm từ assignment active
            current_assignment = self.env['dnu.asset.assignment'].search([
                ('asset_id', '=', self.asset_id.id),
                ('state', '=', 'active'),
                ('id', '!=', self.id),
            ], limit=1)
            if current_assignment and current_assignment.nhan_vien_id:
                current_holder = current_assignment.nhan_vien_id

        # Tạo biên bản bàn giao
        handover = self.env['dnu.asset.handover'].create({
            'handover_type': 'assignment',
            'assignment_id': self.id,
            'asset_id': self.asset_id.id,
            'nhan_vien_id': receiver.id,
            'deliverer_id': current_holder.id if current_holder else False,
            'handover_date': fields.Datetime.now(),
            'condition_handover': 'good',
        })
        
        self.handover_id = handover.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản bàn giao',
            'res_model': 'dnu.asset.handover',
            'res_id': handover.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_handover(self):
        """Mở biên bản bàn giao đã tạo"""
        self.ensure_one()
        if not self.handover_id:
            return self.action_create_handover()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản bàn giao',
            'res_model': 'dnu.asset.handover',
            'res_id': self.handover_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

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
