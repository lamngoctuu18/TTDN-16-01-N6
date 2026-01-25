# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare


class AssetDisposal(models.Model):
    _name = 'dnu.asset.disposal'
    _description = 'Thanh lý tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    def _get_default_responsible(self):
        """Tự động load nhân viên Kiểm kê thuộc phòng Bảo Trì"""
        # Tìm phòng Bảo Trì
        don_vi_bao_tri = self.env['don_vi'].search([
            '|',
            ('ten_don_vi', 'ilike', 'bảo trì'),
            ('ten_don_vi', 'ilike', 'bảo tri')
        ], limit=1)
        
        if not don_vi_bao_tri:
            return self.env.user.employee_id
        
        # Tìm chức vụ Kiểm kê
        chuc_vu_kiem_ke = self.env['chuc_vu'].search([
            '|',
            ('ten_chuc_vu', 'ilike', 'kiểm kê'),
            ('ten_chuc_vu', 'ilike', 'kiem ke')
        ], limit=1)
        
        if not chuc_vu_kiem_ke:
            return self.env.user.employee_id
        
        # Tìm nhân viên có chức vụ Kiểm kê thuộc Bảo Trì
        nhan_vien = self.env['nhan_vien'].search([
            ('don_vi_chinh_id', '=', don_vi_bao_tri.id),
            ('chuc_vu_chinh_id', '=', chuc_vu_kiem_ke.id)
        ], limit=1)
        
        if nhan_vien and nhan_vien.hr_employee_id:
            return nhan_vien.hr_employee_id
        
        return self.env.user.employee_id

    name = fields.Char(
        string='Mã thanh lý',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    date = fields.Date(
        string='Ngày thanh lý',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    disposal_type = fields.Selection([
        ('sale', 'Bán'),
        ('donation', 'Tặng/Quyên góp'),
        ('scrap', 'Hủy/Vứt bỏ'),
        ('return', 'Trả lại nhà cung cấp'),
        ('exchange', 'Đổi mới'),
    ], string='Hình thức thanh lý', required=True, tracking=True)
    
    # Asset
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        tracking=True,
        domain=[('state', '!=', 'disposed')]
    )
    asset_category = fields.Many2one(
        'dnu.asset.category',
        related='asset_id.category_id',
        string='Danh mục',
        store=True
    )
    
    # Financial info
    original_value = fields.Float(
        string='Nguyên giá',
        related='asset_id.purchase_value',
        store=True
    )
    current_value = fields.Float(
        string='Giá trị hiện tại',
        help='Giá trị sổ sách sau khấu hao'
    )
    disposal_value = fields.Float(
        string='Giá thanh lý',
        help='Giá bán hoặc giá trị thu hồi được'
    )

    suggested_disposal_value = fields.Float(
        string='Giá thanh lý đề xuất',
        compute='_compute_suggested_disposal_value',
        readonly=True,
        help='Giá đề xuất dựa trên Giá trị hiện tại và quy tắc cấu hình'
    )
    disposal_value_is_manual = fields.Boolean(
        string='Đã chỉnh tay giá thanh lý',
        default=False,
        help='Nếu đã chỉnh tay, hệ thống sẽ không tự ghi đè giá thanh lý'
    )
    loss_gain = fields.Float(
        string='Lãi/Lỗ',
        compute='_compute_loss_gain',
        store=True,
        help='Chênh lệch giữa giá thanh lý và giá trị hiện tại'
    )
    
    # Reason
    reason = fields.Selection([
        ('obsolete', 'Lỗi thời'),
        ('damaged', 'Hư hỏng không sửa được'),
        ('upgraded', 'Nâng cấp'),
        ('excess', 'Thừa'),
        ('end_life', 'Hết tuổi thọ'),
        ('other', 'Khác'),
    ], string='Lý do thanh lý', required=True, tracking=True)
    reason_detail = fields.Text(string='Chi tiết lý do')
    
    # Approval
    requested_by = fields.Many2one(
        'hr.employee',
        string='Người đề xuất',
        required=True,
        default=lambda self: self._get_default_responsible(),
        domain="[('nhan_vien_id.don_vi_chinh_id.ten_don_vi', 'ilike', 'bảo trì'), ('nhan_vien_id.chuc_vu_chinh_id.ten_chuc_vu', 'ilike', 'kiểm kê')]",
        tracking=True
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        readonly=True,
        tracking=True
    )
    approved_date = fields.Datetime(
        string='Ngày phê duyệt',
        readonly=True
    )
    
    # Buyer/Recipient info (for sale/donation)
    partner_id = fields.Many2one(
        'res.partner',
        string='Đối tác/Người mua',
        help='Áp dụng cho bán hoặc tặng'
    )
    contact_info = fields.Text(string='Thông tin liên hệ')
    
    # Contract/Document
    contract_number = fields.Char(string='Số hợp đồng')
    contract_date = fields.Date(string='Ngày hợp đồng')
    invoice_number = fields.Char(string='Số hóa đơn')
    
    # Documents
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'asset_disposal_attachment_rel',
        'disposal_id',
        'attachment_id',
        string='Tài liệu đính kèm'
    )
    photos = fields.Binary(string='Ảnh tài sản')
    
    # Execution
    executed_by = fields.Many2one(
        'hr.employee',
        string='Người thực hiện',
        domain="[('nhan_vien_id.don_vi_chinh_id.ten_don_vi', 'ilike', 'bảo trì'), ('nhan_vien_id.chuc_vu_chinh_id.ten_chuc_vu', 'ilike', 'kiểm kê')]",
        tracking=True
    )
    executed_date = fields.Date(
        string='Ngày thực hiện',
        tracking=True
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id'
    )
    active = fields.Boolean(default=True)
    batch_id = fields.Many2one(
        'dnu.asset.disposal.batch',
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
        handler_employee = self.requested_by.nhan_vien_id if self.requested_by and hasattr(self.requested_by, 'nhan_vien_id') else False
        department = handler_employee.don_vi_chinh_id if handler_employee else False
        due_date = fields.Date.to_string(self.date) if self.date else False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo văn bản đến',
            'res_model': 'van_ban_den',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_source_model': self._name,
                'default_source_res_id': self.id,
                'default_ten_van_ban': f'Hồ sơ thanh lý {self.name}',
                'default_handler_employee_id': handler_employee.id if handler_employee else False,
                'default_department_id': department.id if department else False,
                'default_due_date': due_date,
            },
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.disposal') or _('New')
        record = super(AssetDisposal, self).create(vals)

        # Auto-fill disposal_value on server-side only if user didn't provide a value
        # and there is a matching rule.
        if not vals.get('disposal_value') and not vals.get('disposal_value_is_manual'):
            rule = record._get_matching_disposal_rule()
            if rule:
                record.disposal_value = record._get_suggested_disposal_value()

        return record

    @api.depends('current_value', 'disposal_value')
    def _compute_loss_gain(self):
        for disposal in self:
            disposal.loss_gain = disposal.disposal_value - disposal.current_value

    @api.depends('current_value', 'disposal_type', 'reason', 'asset_category')
    def _compute_suggested_disposal_value(self):
        for disposal in self:
            disposal.suggested_disposal_value = disposal._get_suggested_disposal_value()

    def _get_matching_disposal_rule(self):
        """Pick the most specific rule for this disposal.

        Specificity priority: category-specific > generic, reason-specific > generic, then sequence.
        """
        self.ensure_one()

        if not self.disposal_type:
            return self.env['dnu.asset.disposal.rule']

        category_id = self.asset_category.id if self.asset_category else False
        domain = [
            ('active', '=', True),
            ('disposal_type', '=', self.disposal_type),
            '|', ('category_id', '=', False), ('category_id', '=', category_id),
            '|', ('reason', '=', False), ('reason', '=', self.reason or False),
        ]
        rules = self.env['dnu.asset.disposal.rule'].search(domain)
        if not rules:
            return rules

        rules = rules.sorted(key=lambda r: (
            0 if r.category_id else 1,
            0 if r.reason else 1,
            r.sequence,
            r.id,
        ))
        return rules[:1]

    def _get_suggested_disposal_value(self):
        self.ensure_one()

        if not self.current_value or self.current_value <= 0:
            return 0.0

        rule = self._get_matching_disposal_rule()
        if not rule:
            return 0.0

        value = self.current_value * (rule.coefficient_percent / 100.0)
        if rule.min_value:
            value = max(value, rule.min_value)
        if rule.max_value:
            value = min(value, rule.max_value)
        return max(value, 0.0)

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Tự động lấy giá trị hiện tại từ khấu hao"""
        if self.asset_id:
            # Tìm khấu hao đang chạy
            depreciation = self.env['dnu.asset.depreciation'].search([
                ('asset_id', '=', self.asset_id.id),
                ('state', '=', 'running'),
            ], limit=1)
            
            if depreciation:
                self.current_value = depreciation.current_value
            else:
                self.current_value = self.asset_id.purchase_value

    @api.onchange('asset_id', 'current_value', 'disposal_type', 'reason')
    def _onchange_autofill_disposal_value(self):
        """Auto-fill Giá thanh lý theo đề xuất nếu người dùng chưa chỉnh tay."""
        for disposal in self:
            if not disposal.asset_id:
                continue
            rule = disposal._get_matching_disposal_rule()
            if rule and not disposal.disposal_value_is_manual:
                disposal.disposal_value = disposal._get_suggested_disposal_value()

    @api.onchange('disposal_value')
    def _onchange_disposal_value_is_manual(self):
        """Mark as manual only when user deviates from suggested price.

        If the price is cleared (0/empty), we allow auto-fill again.
        """
        for disposal in self:
            if not disposal.disposal_value:
                disposal.disposal_value_is_manual = False
                continue

            suggested = disposal._get_suggested_disposal_value()
            rounding = disposal.currency_id.rounding if disposal.currency_id else 0.01
            disposal.disposal_value_is_manual = (
                float_compare(disposal.disposal_value, suggested, precision_rounding=rounding) != 0
            )

    @api.constrains('disposal_value')
    def _check_disposal_value(self):
        for disposal in self:
            if disposal.disposal_value < 0:
                raise ValidationError(_('Giá thanh lý không thể âm!'))

    def action_submit(self):
        """Gửi đề xuất thanh lý"""
        for disposal in self:
            if disposal.state != 'draft':
                raise ValidationError(_('Chỉ có thể gửi đề xuất từ trạng thái Nháp!'))
            
            disposal.write({'state': 'submitted'})
            disposal.message_post(body=_('Đề xuất thanh lý đã được gửi'))
            
            # Tạo activity cho người phê duyệt
            disposal._create_approval_activity()

    def action_approve(self):
        """Phê duyệt thanh lý"""
        for disposal in self:
            if disposal.state != 'submitted':
                raise ValidationError(_('Chỉ có thể phê duyệt ở trạng thái Chờ duyệt!'))
            
            disposal.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            disposal.message_post(body=_('Đề xuất thanh lý đã được phê duyệt'))

    def action_start_execution(self):
        """Bắt đầu thực hiện thanh lý"""
        for disposal in self:
            if disposal.state != 'approved':
                raise ValidationError(_('Chỉ có thể bắt đầu sau khi được phê duyệt!'))
            
            disposal.write({'state': 'in_progress'})
            disposal.message_post(body=_('Bắt đầu thực hiện thanh lý'))

    def action_complete(self):
        """Hoàn thành thanh lý"""
        for disposal in self:
            if disposal.state != 'in_progress':
                raise ValidationError(_('Chỉ có thể hoàn thành khi đang thực hiện!'))
            
            # Cập nhật trạng thái tài sản
            disposal.asset_id.write({
                'state': 'disposed',
                'active': False,
            })
            
            # Kết thúc khấu hao nếu có
            depreciations = self.env['dnu.asset.depreciation'].search([
                ('asset_id', '=', disposal.asset_id.id),
                ('state', '=', 'running'),
            ])
            depreciations.action_complete()
            
            disposal.write({
                'state': 'done',
                'executed_date': fields.Date.today(),
            })
            
            disposal.message_post(
                body=_('Hoàn thành thanh lý tài sản. Giá thanh lý: %s. Lãi/Lỗ: %s') 
                % (disposal.disposal_value, disposal.loss_gain)
            )
            
            # Log vào tài sản
            disposal.asset_id.message_post(
                body=_('Tài sản đã được thanh lý theo %s. Hình thức: %s') 
                % (disposal.name, dict(disposal._fields['disposal_type'].selection).get(disposal.disposal_type))
            )

    def action_cancel(self):
        """Hủy thanh lý"""
        for disposal in self:
            if disposal.state == 'done':
                raise ValidationError(_('Không thể hủy thanh lý đã hoàn thành!'))
            
            disposal.write({'state': 'cancelled'})
            disposal.message_post(body=_('Đã hủy thanh lý'))

    def action_reset_to_draft(self):
        """Reset về nháp"""
        for disposal in self:
            if disposal.state == 'done':
                raise ValidationError(_('Không thể reset thanh lý đã hoàn thành!'))
            
            disposal.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
            })

    def _create_approval_activity(self):
        """Tạo activity yêu cầu phê duyệt"""
        self.ensure_one()
        
        # Tìm người có quyền phê duyệt (ví dụ: quản lý)
        manager_group = self.env.ref('dnu_meeting_asset.group_asset_manager', raise_if_not_found=False)
        if manager_group and manager_group.users:
            for user in manager_group.users:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=_('Phê duyệt thanh lý: %s') % self.name,
                    note=_('Đề xuất thanh lý tài sản %s cần được phê duyệt') % self.asset_id.name,
                )

    def action_print_disposal_report(self):
        """In biên bản thanh lý"""
        self.ensure_one()
        return self.env.ref('dnu_meeting_asset.action_report_asset_disposal').report_action(self)


class AssetDisposalBatch(models.Model):
    _name = 'dnu.asset.disposal.batch'
    _description = 'Thanh lý tài sản hàng loạt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Mã thanh lý hàng loạt',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    date = fields.Date(
        string='Ngày thanh lý',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    disposal_type = fields.Selection([
        ('sale', 'Bán'),
        ('donation', 'Tặng/Quyên góp'),
        ('scrap', 'Hủy/Vứt bỏ'),
        ('return', 'Trả lại nhà cung cấp'),
        ('exchange', 'Đổi mới'),
    ], string='Hình thức thanh lý', required=True)
    
    reason = fields.Selection([
        ('obsolete', 'Lỗi thời'),
        ('damaged', 'Hư hỏng không sửa được'),
        ('upgraded', 'Nâng cấp'),
        ('excess', 'Thừa'),
        ('end_life', 'Hết tuổi thọ'),
        ('other', 'Khác'),
    ], string='Lý do thanh lý', required=True)
    
    asset_ids = fields.Many2many(
        'dnu.asset',
        string='Tài sản',
        domain=[('state', '!=', 'disposed')]
    )
    
    disposal_ids = fields.One2many(
        'dnu.asset.disposal',
        'batch_id',
        string='Thanh lý'
    )
    
    total_original_value = fields.Float(
        string='Tổng nguyên giá',
        compute='_compute_totals',
        store=True
    )
    total_disposal_value = fields.Float(
        string='Tổng giá thanh lý',
        compute='_compute_totals',
        store=True
    )
    total_loss_gain = fields.Float(
        string='Tổng lãi/lỗ',
        compute='_compute_totals',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('processing', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    partner_id = fields.Many2one('res.partner', string='Đối tác/Người mua')
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.disposal.batch') or _('New')
        return super(AssetDisposalBatch, self).create(vals)

    @api.depends('disposal_ids.original_value', 'disposal_ids.disposal_value', 'disposal_ids.loss_gain')
    def _compute_totals(self):
        for batch in self:
            batch.total_original_value = sum(batch.disposal_ids.mapped('original_value'))
            batch.total_disposal_value = sum(batch.disposal_ids.mapped('disposal_value'))
            batch.total_loss_gain = sum(batch.disposal_ids.mapped('loss_gain'))

    def action_generate_disposals(self):
        """Tạo các thanh lý từ danh sách tài sản"""
        self.ensure_one()
        
        if not self.asset_ids:
            raise UserError(_('Vui lòng chọn ít nhất một tài sản!'))
        
        # Xóa disposals cũ nếu có
        self.disposal_ids.unlink()
        
        Disposal = self.env['dnu.asset.disposal']
        
        for asset in self.asset_ids:
            # Tìm giá trị hiện tại
            current_value = asset.purchase_value
            depreciation = self.env['dnu.asset.depreciation'].search([
                ('asset_id', '=', asset.id),
                ('state', '=', 'running'),
            ], limit=1)
            if depreciation:
                current_value = depreciation.current_value
            
            Disposal.create({
                'asset_id': asset.id,
                'disposal_type': self.disposal_type,
                'reason': self.reason,
                'date': self.date,
                'current_value': current_value,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'batch_id': self.id,
                'state': 'draft',
            })
        
        self.write({'state': 'processing'})
        self.message_post(body=_('Đã tạo %d thanh lý') % len(self.asset_ids))

    def action_complete_all(self):
        """Hoàn thành tất cả thanh lý"""
        self.ensure_one()
        
        for disposal in self.disposal_ids:
            if disposal.state == 'draft':
                disposal.action_submit()
                disposal.action_approve()
                disposal.action_start_execution()
                disposal.action_complete()
        
        self.write({'state': 'done'})
