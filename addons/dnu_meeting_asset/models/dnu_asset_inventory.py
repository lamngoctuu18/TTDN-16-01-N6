# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AssetInventory(models.Model):
    _name = 'dnu.asset.inventory'
    _description = 'Kiểm kê tài sản'
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

    def _get_default_team(self):
        """Tự động load đội kiểm kê từ phòng Bảo Trì"""
        # Tìm phòng Bảo Trì
        don_vi_bao_tri = self.env['don_vi'].search([
            '|',
            ('ten_don_vi', 'ilike', 'bảo trì'),
            ('ten_don_vi', 'ilike', 'bảo tri')
        ], limit=1)
        
        if not don_vi_bao_tri:
            return False
        
        # Tìm tất cả nhân viên thuộc phòng Bảo Trì
        nhan_viens = self.env['nhan_vien'].search([
            ('don_vi_chinh_id', '=', don_vi_bao_tri.id)
        ])
        
        if nhan_viens:
            hr_employees = nhan_viens.filtered(lambda n: n.hr_employee_id).mapped('hr_employee_id')
            return hr_employees.ids if hr_employees else False
        
        return False

    name = fields.Char(
        string='Mã kiểm kê',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    date = fields.Date(
        string='Ngày kiểm kê',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    inventory_type = fields.Selection([
        ('periodic', 'Kiểm kê định kỳ'),
        ('spot', 'Kiểm kê đột xuất'),
        ('annual', 'Kiểm kê cuối năm'),
    ], string='Loại kiểm kê', default='periodic', required=True, tracking=True)
    
    # Scope
    scope = fields.Selection([
        ('all', 'Toàn bộ tài sản'),
        ('category', 'Theo danh mục'),
        ('department', 'Theo phòng ban'),
        ('location', 'Theo vị trí'),
        ('custom', 'Tùy chỉnh'),
    ], string='Phạm vi kiểm kê', default='all', required=True)
    
    category_ids = fields.Many2many(
        'dnu.asset.category',
        string='Danh mục tài sản',
        help='Áp dụng khi kiểm kê theo danh mục'
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Phòng ban',
        help='Áp dụng khi kiểm kê theo phòng ban'
    )
    location_ids = fields.Char(
        string='Vị trí',
        help='Danh sách các vị trí cần kiểm kê, phân cách bằng dấu phẩy'
    )
    
    # Team
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Người chịu trách nhiệm',
        required=True,
        default=lambda self: self._get_default_responsible(),
        domain="[('nhan_vien_id.don_vi_chinh_id.ten_don_vi', 'ilike', 'bảo trì'), ('nhan_vien_id.chuc_vu_chinh_id.ten_chuc_vu', 'ilike', 'kiểm kê')]",
        tracking=True
    )
    team_ids = fields.Many2many(
        'hr.employee',
        'inventory_team_rel',
        'inventory_id',
        'employee_id',
        string='Đội kiểm kê',
        default=lambda self: self._get_default_team(),
        domain="[('nhan_vien_id.don_vi_chinh_id.ten_don_vi', 'ilike', 'bảo trì')]"
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang kiểm kê'),
        ('review', 'Chờ duyệt'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # Lines
    line_ids = fields.One2many(
        'dnu.asset.inventory.line',
        'inventory_id',
        string='Chi tiết kiểm kê'
    )
    
    # Statistics
    total_assets = fields.Integer(
        string='Tổng số tài sản',
        compute='_compute_statistics',
        store=True
    )
    checked_assets = fields.Integer(
        string='Đã kiểm',
        compute='_compute_statistics',
        store=True
    )
    found_assets = fields.Integer(
        string='Tìm thấy',
        compute='_compute_statistics',
        store=True
    )
    missing_assets = fields.Integer(
        string='Mất/Hỏng',
        compute='_compute_statistics',
        store=True
    )
    extra_assets = fields.Integer(
        string='Thừa',
        compute='_compute_statistics',
        store=True
    )
    completion_rate = fields.Float(
        string='Tỷ lệ hoàn thành (%)',
        compute='_compute_statistics',
        store=True
    )
    
    # Dates
    start_date = fields.Datetime(
        string='Ngày bắt đầu',
        tracking=True
    )
    end_date = fields.Datetime(
        string='Ngày kết thúc',
        tracking=True
    )
    
    # Report
    summary = fields.Html(string='Tóm tắt kết quả')
    notes = fields.Text(string='Ghi chú')
    recommendations = fields.Text(string='Kiến nghị')
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.inventory') or _('New')
        return super(AssetInventory, self).create(vals)

    @api.depends('line_ids', 'line_ids.state', 'line_ids.status')
    def _compute_statistics(self):
        for inventory in self:
            lines = inventory.line_ids
            inventory.total_assets = len(lines)
            inventory.checked_assets = len(lines.filtered(lambda l: l.state == 'checked'))
            inventory.found_assets = len(lines.filtered(lambda l: l.status == 'found'))
            inventory.missing_assets = len(lines.filtered(lambda l: l.status in ['missing', 'damaged']))
            inventory.extra_assets = len(lines.filtered(lambda l: l.status == 'extra'))
            
            if inventory.total_assets > 0:
                inventory.completion_rate = (inventory.checked_assets / inventory.total_assets) * 100
            else:
                inventory.completion_rate = 0.0

    def action_generate_inventory(self):
        """Tạo danh sách tài sản cần kiểm kê"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise ValidationError(_('Chỉ có thể tạo danh sách từ trạng thái Nháp!'))
        
        # Xóa dòng cũ nếu có
        self.line_ids.unlink()
        
        # Tìm tài sản theo phạm vi
        domain = self._get_asset_domain()
        assets = self.env['dnu.asset'].search(domain)
        
        if not assets:
            raise UserError(_('Không tìm thấy tài sản nào trong phạm vi kiểm kê!'))
        
        # Tạo dòng kiểm kê
        InventoryLine = self.env['dnu.asset.inventory.line']
        for asset in assets:
            InventoryLine.create({
                'inventory_id': self.id,
                'asset_id': asset.id,
                'expected_location': asset.location,
                'expected_assigned_to': asset.assigned_to.id if asset.assigned_to else False,
                'state': 'pending',
            })
        
        self.message_post(body=_('Đã tạo danh sách kiểm kê với %d tài sản') % len(assets))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã tạo danh sách kiểm kê với %d tài sản') % len(assets),
                'type': 'success',
            }
        }

    def _get_asset_domain(self):
        """Xây dựng domain để tìm tài sản theo phạm vi"""
        domain = [('state', '!=', 'disposed')]
        
        if self.scope == 'category' and self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        
        elif self.scope == 'department' and self.department_ids:
            domain.append(('assigned_to.department_id', 'in', self.department_ids.ids))
        
        elif self.scope == 'location' and self.location_ids:
            locations = [loc.strip() for loc in self.location_ids.split(',')]
            domain.append(('location', 'in', locations))
        
        return domain

    def action_start(self):
        """Bắt đầu kiểm kê"""
        for inventory in self:
            if not inventory.line_ids:
                raise ValidationError(_('Vui lòng tạo danh sách tài sản trước khi bắt đầu!'))
            
            inventory.write({
                'state': 'in_progress',
                'start_date': fields.Datetime.now(),
            })
            inventory.message_post(body=_('Bắt đầu kiểm kê tài sản'))

    def action_submit_review(self):
        """Gửi kiểm kê để duyệt"""
        self.ensure_one()
        
        if self.state != 'in_progress':
            raise ValidationError(_('Chỉ có thể gửi duyệt khi đang kiểm kê!'))
        
        # Kiểm tra xem đã kiểm đủ chưa
        unchecked = self.line_ids.filtered(lambda l: l.state == 'pending')
        if unchecked:
            raise ValidationError(
                _('Còn %d tài sản chưa được kiểm! Vui lòng hoàn thành trước khi gửi duyệt.') 
                % len(unchecked)
            )
        
        self.write({
            'state': 'review',
            'end_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Đã gửi kết quả kiểm kê để duyệt'))
        
        # Tạo tóm tắt tự động
        self._generate_summary()

    def action_approve(self):
        """Duyệt kết quả kiểm kê"""
        for inventory in self:
            if inventory.state != 'review':
                raise ValidationError(_('Chỉ có thể duyệt kiểm kê ở trạng thái Chờ duyệt!'))
            
            inventory.write({'state': 'done'})
            
            # Cập nhật trạng thái tài sản theo kết quả kiểm kê
            inventory._apply_inventory_results()
            
            inventory.message_post(body=_('Đã duyệt kết quả kiểm kê'))

    def action_cancel(self):
        """Hủy kiểm kê"""
        for inventory in self:
            inventory.write({'state': 'cancelled'})
            inventory.message_post(body=_('Đã hủy kiểm kê'))

    def action_reset_to_draft(self):
        """Reset về nháp"""
        for inventory in self:
            if inventory.state == 'done':
                raise ValidationError(_('Không thể reset kiểm kê đã hoàn thành!'))
            
            inventory.write({
                'state': 'draft',
                'start_date': False,
                'end_date': False,
            })
            inventory.line_ids.write({'state': 'pending'})

    def _generate_summary(self):
        """Tự động tạo tóm tắt kết quả"""
        self.ensure_one()
        
        summary = '''
        <h3>Kết quả kiểm kê: %s</h3>
        <ul>
            <li>Tổng số tài sản: <strong>%d</strong></li>
            <li>Tìm thấy: <strong>%d</strong> (%.1f%%)</li>
            <li>Mất/Hỏng: <strong>%d</strong> (%.1f%%)</li>
            <li>Thừa: <strong>%d</strong></li>
        </ul>
        ''' % (
            self.name,
            self.total_assets,
            self.found_assets,
            (self.found_assets / self.total_assets * 100) if self.total_assets else 0,
            self.missing_assets,
            (self.missing_assets / self.total_assets * 100) if self.total_assets else 0,
            self.extra_assets,
        )
        
        # Liệt kê tài sản có vấn đề
        problem_lines = self.line_ids.filtered(lambda l: l.status != 'found')
        if problem_lines:
            summary += '<h4>Tài sản có vấn đề:</h4><ul>'
            for line in problem_lines:
                summary += '<li>%s - %s: <strong>%s</strong></li>' % (
                    line.asset_id.code,
                    line.asset_id.name,
                    dict(line._fields['status'].selection).get(line.status)
                )
            summary += '</ul>'
        
        self.summary = summary

    def _apply_inventory_results(self):
        """Áp dụng kết quả kiểm kê lên tài sản"""
        self.ensure_one()
        
        for line in self.line_ids:
            asset = line.asset_id
            
            # Cập nhật vị trí thực tế
            if line.actual_location and line.actual_location != line.expected_location:
                asset.location = line.actual_location
            
            # Cập nhật người được gán
            if line.actual_assigned_to and line.actual_assigned_to != line.expected_assigned_to:
                asset.assigned_to = line.actual_assigned_to
            
            # Đánh dấu tài sản mất
            if line.status == 'missing':
                asset.message_post(body=_('Tài sản được đánh dấu là MẤT trong kiểm kê %s') % self.name)
            
            # Đánh dấu tài sản hỏng
            elif line.status == 'damaged':
                asset.state = 'maintenance'
                asset.message_post(body=_('Tài sản được đánh dấu là HỎNG trong kiểm kê %s. Chuyển sang bảo trì.') % self.name)

    def action_print_report(self):
        """In báo cáo kiểm kê"""
        self.ensure_one()
        return self.env.ref('dnu_meeting_asset.action_report_asset_inventory').report_action(self)


class AssetInventoryLine(models.Model):
    _name = 'dnu.asset.inventory.line'
    _description = 'Dòng kiểm kê tài sản'
    _order = 'asset_id'

    inventory_id = fields.Many2one(
        'dnu.asset.inventory',
        string='Kiểm kê',
        required=True,
        ondelete='cascade'
    )
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True
    )
    
    # Expected (from system)
    expected_location = fields.Char(string='Vị trí dự kiến')
    expected_assigned_to = fields.Many2one(
        'hr.employee',
        string='Người giữ dự kiến'
    )
    
    # Actual (from inventory)
    actual_location = fields.Char(string='Vị trí thực tế')
    actual_assigned_to = fields.Many2one(
        'hr.employee',
        string='Người giữ thực tế'
    )
    
    # Status
    state = fields.Selection([
        ('pending', 'Chờ kiểm'),
        ('checked', 'Đã kiểm'),
    ], string='Trạng thái', default='pending', required=True)
    
    status = fields.Selection([
        ('found', 'Tìm thấy'),
        ('missing', 'Mất'),
        ('damaged', 'Hỏng'),
        ('extra', 'Thừa'),
    ], string='Kết quả')
    
    # Check info
    checked_date = fields.Datetime(string='Ngày kiểm')
    checked_by = fields.Many2one(
        'hr.employee',
        string='Người kiểm'
    )
    condition = fields.Selection([
        ('good', 'Tốt'),
        ('normal', 'Bình thường'),
        ('poor', 'Kém'),
    ], string='Tình trạng')
    
    notes = fields.Text(string='Ghi chú')
    photo = fields.Binary(string='Ảnh chụp')

    def action_mark_found(self):
        """Đánh dấu tìm thấy"""
        for line in self:
            line.write({
                'state': 'checked',
                'status': 'found',
                'checked_date': fields.Datetime.now(),
                'checked_by': self.env.user.employee_id.id,
            })

    def action_mark_missing(self):
        """Đánh dấu mất"""
        for line in self:
            line.write({
                'state': 'checked',
                'status': 'missing',
                'checked_date': fields.Datetime.now(),
                'checked_by': self.env.user.employee_id.id,
            })

    def action_mark_damaged(self):
        """Đánh dấu hỏng"""
        for line in self:
            line.write({
                'state': 'checked',
                'status': 'damaged',
                'checked_date': fields.Datetime.now(),
                'checked_by': self.env.user.employee_id.id,
            })

    def action_quick_check(self):
        """Kiểm tra nhanh - tự động điền thông tin từ hệ thống"""
        for line in self:
            asset = line.asset_id
            line.write({
                'actual_location': asset.location,
                'actual_assigned_to': asset.assigned_to.id if asset.assigned_to else False,
                'condition': 'good',
            })
