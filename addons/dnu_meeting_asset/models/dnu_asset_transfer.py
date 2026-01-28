# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AssetTransfer(models.Model):
    _name = 'dnu.asset.transfer'
    _description = 'Luân chuyển tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Mã luân chuyển',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    date = fields.Date(
        string='Ngày luân chuyển',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    transfer_type = fields.Selection([
        ('employee', 'Giữa nhân viên'),
        ('department', 'Giữa phòng ban'),
        ('location', 'Giữa vị trí'),
    ], string='Loại luân chuyển', default='employee', required=True, tracking=True)
    
    # Asset
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        tracking=True
    )
    
    # From
    from_employee_id = fields.Many2one(
        'nhan_vien',
        string='Từ nhân viên',
        tracking=True
    )
    from_department_id = fields.Many2one(
        'don_vi',
        string='Từ phòng ban',
        tracking=True
    )
    from_location = fields.Char(
        string='Từ vị trí',
        tracking=True
    )
    
    # To
    to_employee_id = fields.Many2one(
        'nhan_vien',
        string='Đến nhân viên',
        tracking=True
    )
    to_department_id = fields.Many2one(
        'don_vi',
        string='Đến phòng ban',
        tracking=True
    )
    to_location = fields.Char(
        string='Đến vị trí',
        tracking=True
    )
    
    # Reason
    reason = fields.Selection([
        ('reassignment', 'Tái phân bổ'),
        ('replacement', 'Thay thế'),
        ('repair', 'Sửa chữa'),
        ('upgrade', 'Nâng cấp'),
        ('relocation', 'Di chuyển văn phòng'),
        ('other', 'Khác'),
    ], string='Lý do', required=True, tracking=True)
    reason_detail = fields.Text(string='Chi tiết lý do')
    
    # Handover
    handover_date = fields.Date(
        string='Ngày bàn giao',
        tracking=True
    )
    handover_by = fields.Many2one(
        'nhan_vien',
        string='Người bàn giao',
        tracking=True
    )
    received_by = fields.Many2one(
        'nhan_vien',
        string='Người nhận',
        tracking=True
    )
    witness_ids = fields.Many2many(
        'nhan_vien',
        'transfer_witness_rel',
        'transfer_id',
        'employee_id',
        string='Người chứng kiến'
    )
    
    # Condition check
    condition_before = fields.Selection([
        ('good', 'Tốt'),
        ('normal', 'Bình thường'),
        ('poor', 'Kém'),
    ], string='Tình trạng trước chuyển', tracking=True)
    
    condition_after = fields.Selection([
        ('good', 'Tốt'),
        ('normal', 'Bình thường'),
        ('poor', 'Kém'),
    ], string='Tình trạng sau chuyển', tracking=True)
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'asset_transfer_attachment_rel',
        'transfer_id',
        'attachment_id',
        string='Biên bản bàn giao'
    )
    photos_before = fields.Binary(string='Ảnh trước chuyển')
    photos_after = fields.Binary(string='Ảnh sau chuyển')
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('in_transit', 'Đang chuyển'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # Approvals
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt',
        readonly=True
    )
    approved_date = fields.Datetime(
        string='Ngày duyệt',
        readonly=True
    )
    
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)
    batch_id = fields.Many2one(
        'dnu.asset.transfer.batch',
        string='Batch',
        ondelete='set null'
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
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo văn bản đến',
            'res_model': 'van_ban_den',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_source_model': self._name,
                'default_source_res_id': self.id,
                'default_ten_van_ban': f'Văn bản đến - Luân chuyển {self.name}',
                'default_due_date': fields.Date.to_string(self.date) if self.date else False,
            },
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.transfer') or _('New')
        return super(AssetTransfer, self).create(vals)

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Tự động điền thông tin hiện tại của tài sản"""
        if self.asset_id:
            self.from_employee_id = self.asset_id.assigned_nhan_vien_id
            self.from_department_id = self.asset_id.assigned_nhan_vien_id.don_vi_chinh_id if self.asset_id.assigned_nhan_vien_id else False
            self.from_location = self.asset_id.location

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        """Reset các trường không liên quan khi đổi loại"""
        if self.transfer_type == 'employee':
            self.to_department_id = False
            self.to_location = False
        elif self.transfer_type == 'department':
            self.to_employee_id = False
            self.to_location = False
        elif self.transfer_type == 'location':
            self.to_employee_id = False
            self.to_department_id = False

    @api.constrains('asset_id', 'from_employee_id', 'to_employee_id')
    def _check_transfer(self):
        """Kiểm tra tính hợp lệ của luân chuyển"""
        for transfer in self:
            # Không thể chuyển cho cùng một người
            if transfer.transfer_type == 'employee':
                if not transfer.to_employee_id:
                    raise ValidationError(_('Vui lòng chọn nhân viên nhận!'))
                if transfer.from_employee_id == transfer.to_employee_id:
                    raise ValidationError(_('Không thể chuyển tài sản cho cùng một nhân viên!'))
            
            # Phòng ban
            elif transfer.transfer_type == 'department':
                if not transfer.to_department_id:
                    raise ValidationError(_('Vui lòng chọn phòng ban nhận!'))
                if transfer.from_department_id == transfer.to_department_id:
                    raise ValidationError(_('Không thể chuyển tài sản cho cùng một phòng ban!'))
            
            # Vị trí
            elif transfer.transfer_type == 'location':
                if not transfer.to_location:
                    raise ValidationError(_('Vui lòng nhập vị trí mới!'))
                if transfer.from_location == transfer.to_location:
                    raise ValidationError(_('Không thể chuyển tài sản đến cùng một vị trí!'))

    def action_submit(self):
        """Gửi yêu cầu luân chuyển"""
        for transfer in self:
            if transfer.state != 'draft':
                raise ValidationError(_('Chỉ có thể gửi yêu cầu từ trạng thái Nháp!'))
            
            transfer.write({'state': 'submitted'})
            transfer.message_post(body=_('Yêu cầu luân chuyển đã được gửi'))

    def action_approve(self):
        """Duyệt yêu cầu luân chuyển"""
        for transfer in self:
            if transfer.state != 'submitted':
                raise ValidationError(_('Chỉ có thể duyệt yêu cầu ở trạng thái Chờ duyệt!'))
            
            transfer.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            transfer.message_post(body=_('Yêu cầu luân chuyển đã được duyệt'))

    def action_start_transfer(self):
        """Bắt đầu quá trình luân chuyển"""
        for transfer in self:
            if transfer.state != 'approved':
                raise ValidationError(_('Chỉ có thể bắt đầu luân chuyển sau khi được duyệt!'))
            
            transfer.write({'state': 'in_transit'})
            transfer.message_post(body=_('Bắt đầu luân chuyển tài sản'))

    def action_complete(self):
        """Hoàn thành luân chuyển"""
        for transfer in self:
            if transfer.state != 'in_transit':
                raise ValidationError(_('Chỉ có thể hoàn thành khi đang trong quá trình luân chuyển!'))
            
            # Cập nhật thông tin tài sản
            transfer._update_asset_info()
            
            # Tạo assignment mới nếu cần
            if transfer.transfer_type == 'employee' and transfer.to_employee_id:
                transfer._create_assignment()
            
            transfer.write({
                'state': 'completed',
                'handover_date': fields.Date.today(),
            })
            transfer.message_post(body=_('Hoàn thành luân chuyển tài sản'))

    def action_cancel(self):
        """Hủy luân chuyển"""
        for transfer in self:
            if transfer.state == 'completed':
                raise ValidationError(_('Không thể hủy luân chuyển đã hoàn thành!'))
            
            transfer.write({'state': 'cancelled'})
            transfer.message_post(body=_('Đã hủy luân chuyển'))

    def action_reset_to_draft(self):
        """Reset về nháp"""
        for transfer in self:
            if transfer.state == 'completed':
                raise ValidationError(_('Không thể reset luân chuyển đã hoàn thành!'))
            
            transfer.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
            })

    def _update_asset_info(self):
        """Cập nhật thông tin tài sản sau khi luân chuyển"""
        self.ensure_one()
        
        asset = self.asset_id
        vals = {}
        
        if self.transfer_type == 'employee':
            vals['assigned_nhan_vien_id'] = self.to_employee_id.id
            vals['assigned_to'] = False  # Clear hr.employee assignment since using custom HR
            vals['assignment_date'] = fields.Date.today()
            if self.to_employee_id.don_vi_chinh_id:
                vals['location'] = self.to_employee_id.don_vi_chinh_id.ten_don_vi
        
        elif self.transfer_type == 'department':
            vals['assigned_nhan_vien_id'] = False  # Không gán cho ai
            vals['assigned_to'] = False  # Clear hr.employee assignment
            vals['location'] = self.to_department_id.ten_don_vi
        
        elif self.transfer_type == 'location':
            vals['location'] = self.to_location
        
        if vals:
            asset.write(vals)
            asset.message_post(
                body=_('Tài sản đã được luân chuyển theo %s') % self.name
            )

    def _create_assignment(self):
        """Tạo bản ghi assignment mới"""
        self.ensure_one()
        
        # Kết thúc assignment cũ nếu có
        old_assignments = self.env['dnu.asset.assignment'].search([
            ('asset_id', '=', self.asset_id.id),
            ('state', '=', 'active'),
        ])
        old_assignments.write({
            'state': 'returned',
            'date_to': fields.Date.today(),
        })
        
        # Tạo assignment mới
        self.env['dnu.asset.assignment'].create({
            'asset_id': self.asset_id.id,
            'nhan_vien_id': self.to_employee_id.id,
            'date_from': fields.Date.today(),
            'state': 'active',
            'notes': _('Được tạo từ luân chuyển %s') % self.name,
        })

    def action_print_handover_document(self):
        """In biên bản bàn giao"""
        self.ensure_one()
        return self.env.ref('dnu_meeting_asset.action_report_asset_transfer').report_action(self)


class AssetTransferBatch(models.Model):
    _name = 'dnu.asset.transfer.batch'
    _description = 'Luân chuyển tài sản hàng loạt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Mã luân chuyển hàng loạt',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    date = fields.Date(
        string='Ngày thực hiện',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    # Selection criteria
    transfer_type = fields.Selection([
        ('employee', 'Giữa nhân viên'),
        ('department', 'Giữa phòng ban'),
        ('location', 'Giữa vị trí'),
    ], string='Loại luân chuyển', required=True)
    
    asset_ids = fields.Many2many(
        'dnu.asset',
        string='Tài sản',
        required=True
    )
    
    # Target
    to_employee_id = fields.Many2one('hr.employee', string='Đến nhân viên')
    to_department_id = fields.Many2one('hr.department', string='Đến phòng ban')
    to_location = fields.Char(string='Đến vị trí')
    
    # Generated transfers
    transfer_ids = fields.One2many(
        'dnu.asset.transfer',
        'batch_id',
        string='Luân chuyển'
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('processing', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.transfer.batch') or _('New')
        return super(AssetTransferBatch, self).create(vals)

    def action_generate_transfers(self):
        """Tạo các luân chuyển từ danh sách tài sản"""
        self.ensure_one()
        
        if not self.asset_ids:
            raise UserError(_('Vui lòng chọn ít nhất một tài sản!'))
        
        # Xóa transfers cũ nếu có
        self.transfer_ids.unlink()
        
        Transfer = self.env['dnu.asset.transfer']
        
        for asset in self.asset_ids:
            vals = {
                'asset_id': asset.id,
                'transfer_type': self.transfer_type,
                'date': self.date,
                'batch_id': self.id,
                'state': 'draft',
            }
            
            # From
            vals['from_employee_id'] = asset.assigned_to.id if asset.assigned_to else False
            vals['from_department_id'] = asset.assigned_to.department_id.id if asset.assigned_to and asset.assigned_to.department_id else False
            vals['from_location'] = asset.location
            
            # To
            if self.transfer_type == 'employee':
                vals['to_employee_id'] = self.to_employee_id.id
            elif self.transfer_type == 'department':
                vals['to_department_id'] = self.to_department_id.id
            elif self.transfer_type == 'location':
                vals['to_location'] = self.to_location
            
            Transfer.create(vals)
        
        self.write({'state': 'processing'})
        self.message_post(body=_('Đã tạo %d luân chuyển') % len(self.asset_ids))

    def action_complete_all(self):
        """Hoàn thành tất cả luân chuyển"""
        self.ensure_one()
        
        for transfer in self.transfer_ids:
            if transfer.state == 'draft':
                transfer.action_submit()
                transfer.action_approve()
                transfer.action_start_transfer()
                transfer.action_complete()
        
        self.write({'state': 'done'})
