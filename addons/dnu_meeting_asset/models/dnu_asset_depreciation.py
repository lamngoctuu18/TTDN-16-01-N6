# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class AssetDepreciation(models.Model):
    _name = 'dnu.asset.depreciation'
    _description = 'Khấu hao tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(
        string='Mã khấu hao',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        tracking=True,
        ondelete='cascade'
    )
    method = fields.Selection([
        ('linear', 'Khấu hao đường thẳng'),
        ('declining', 'Khấu hao số dư giảm dần'),
        ('manual', 'Khấu hao thủ công'),
    ], string='Phương pháp khấu hao', default='linear', required=True, tracking=True)
    
    # Depreciation info
    purchase_value = fields.Float(
        string='Nguyên giá',
        required=True,
        tracking=True,
        help='Giá trị ban đầu của tài sản'
    )
    salvage_value = fields.Float(
        string='Giá trị thanh lý',
        default=0.0,
        help='Giá trị còn lại sau khi khấu hao hết'
    )
    depreciation_total = fields.Float(
        string='Tổng giá trị khấu hao',
        compute='_compute_depreciation_totals',
        store=True,
        help='Tổng giá trị cần khấu hao = Nguyên giá - Giá trị thanh lý'
    )
    depreciation_value = fields.Float(
        string='Giá trị khấu hao (mỗi kỳ)',
        compute='_compute_depreciation_value',
        store=True,
        help='Giá trị khấu hao của một kỳ. Với phương pháp số dư giảm dần, giá trị thay đổi theo kỳ.'
    )
    current_value = fields.Float(
        string='Giá trị hiện tại',
        compute='_compute_current_value',
        store=True,
        help='Nguyên giá - Tổng khấu hao đã tính'
    )
    
    # Period
    start_date = fields.Date(
        string='Ngày bắt đầu khấu hao',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    end_date = fields.Date(
        string='Ngày kết thúc khấu hao',
        compute='_compute_end_date',
        store=True
    )
    useful_life = fields.Integer(
        string='Thời gian sử dụng (tháng)',
        default=60,
        required=True,
        help='Số tháng sử dụng dự kiến của tài sản'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('running', 'Đang khấu hao'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # Depreciation lines
    depreciation_line_ids = fields.One2many(
        'dnu.asset.depreciation.line',
        'depreciation_id',
        string='Chi tiết khấu hao'
    )
    total_depreciated = fields.Float(
        string='Tổng đã khấu hao',
        compute='_compute_total_depreciated',
        store=True
    )
    depreciation_rate = fields.Float(
        string='Tỷ lệ khấu hao (%)',
        compute='_compute_depreciation_rate',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        related='company_id.currency_id'
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Ghi chú')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.depreciation') or _('New')
        return super(AssetDepreciation, self).create(vals)

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Tự động load nguyên giá từ tài sản được chọn"""
        if self.asset_id:
            self.purchase_value = self.asset_id.purchase_value
            # Tự động set giá trị thanh lý theo phương thức đang chọn
            self._onchange_method()

    @api.onchange('method', 'purchase_value', 'useful_life')
    def _onchange_method(self):
        """Tự động tính giá trị thanh lý theo phương thức khấu hao"""
        if self.method and self.purchase_value:
            if self.method == 'linear':
                # Phương pháp đường thẳng: GT_TL = 0
                self.salvage_value = 0.0
            elif self.method == 'declining':
                # Phương pháp số dư giảm dần: khuyến nghị nhập GT_TL thủ công nếu có
                # Mặc định GT_TL = 0 để tránh tính sai theo tháng/năm
                self.salvage_value = 0.0
            else:
                # Phương pháp thủ công: giữ nguyên hoặc set = 0
                if not self.salvage_value:
                    self.salvage_value = 0.0

    @api.depends('purchase_value', 'salvage_value')
    def _compute_depreciation_totals(self):
        for record in self:
            record.depreciation_total = record.purchase_value - record.salvage_value

    @api.depends('method', 'purchase_value', 'salvage_value', 'useful_life')
    def _compute_depreciation_value(self):
        """Tính giá trị khấu hao của một kỳ"""
        for record in self:
            if record.purchase_value <= 0 or record.useful_life <= 0:
                record.depreciation_value = 0.0
                continue

            if record.method == 'linear':
                record.depreciation_value = record.depreciation_total / record.useful_life
            elif record.method == 'declining':
                # Số dư giảm dần: giá trị khấu hao thay đổi theo kỳ
                record.depreciation_value = 0.0
            else:
                record.depreciation_value = 0.0

    @api.depends('purchase_value', 'total_depreciated', 'salvage_value')
    def _compute_current_value(self):
        for record in self:
            remaining = record.purchase_value - record.total_depreciated
            if record.salvage_value and remaining < record.salvage_value:
                remaining = record.salvage_value
            record.current_value = remaining

    @api.depends('start_date', 'useful_life', 'depreciation_line_ids.date')
    def _compute_end_date(self):
        for record in self:
            if record.depreciation_line_ids:
                record.end_date = max(record.depreciation_line_ids.mapped('date'))
            elif record.start_date and record.useful_life:
                record.end_date = record.start_date + relativedelta(months=record.useful_life)
            else:
                record.end_date = False

    @api.depends('depreciation_line_ids.amount', 'depreciation_line_ids.state')
    def _compute_total_depreciated(self):
        for record in self:
            posted_lines = record.depreciation_line_ids.filtered(lambda l: l.state == 'posted')
            record.total_depreciated = sum(posted_lines.mapped('amount'))

    @api.depends('method', 'depreciation_value', 'purchase_value')
    def _compute_depreciation_rate(self):
        """Tính tỷ lệ khấu hao theo từng phương pháp"""
        for record in self:
            if record.purchase_value <= 0:
                record.depreciation_rate = 0.0
                continue

            # Tỷ lệ kỳ = KH kỳ / NG (widget percentage yêu cầu giá trị 0..1)
            record.depreciation_rate = (record.depreciation_value / record.purchase_value) if record.depreciation_value else 0.0

    @api.constrains('purchase_value', 'salvage_value')
    def _check_values(self):
        """Kiểm tra ràng buộc về giá trị"""
        for record in self:
            if record.purchase_value <= 0:
                raise ValidationError(_('Nguyên giá phải lớn hơn 0!'))
            if record.salvage_value < 0:
                raise ValidationError(_('Giá trị thanh lý không thể âm!'))
            if record.salvage_value >= record.purchase_value:
                raise ValidationError(_('Giá trị thanh lý phải nhỏ hơn nguyên giá!'))

    @api.constrains('useful_life')
    def _check_useful_life(self):
        """Kiểm tra thời gian sử dụng"""
        for record in self:
            if record.useful_life <= 0:
                raise ValidationError(_('Thời gian sử dụng phải lớn hơn 0!'))
    
    @api.constrains('depreciation_line_ids', 'depreciation_total')
    def _check_total_depreciation(self):
        """Kiểm tra tổng khấu hao không vượt quá (NG - GT_TL)"""
        for record in self:
            if record.method == 'manual':
                total_manual = sum(record.depreciation_line_ids.mapped('amount'))
                if total_manual > record.depreciation_total:
                    raise ValidationError(_(
                        'Tổng khấu hao thủ công (%s) không được vượt quá tổng giá trị khấu hao (%s)!'
                    ) % (total_manual, record.depreciation_total))
    
    def action_regenerate_lines(self):
        """Tạo lại bảng khấu hao khi thay đổi thông số"""
        for record in self:
            if record.state == 'draft':
                # Xóa các dòng cũ
                record.depreciation_line_ids.unlink()
                
                # Tạo lại dòng khấu hao
                if record.method == 'linear':
                    record._create_linear_depreciation_lines()
                elif record.method == 'declining':
                    record._create_declining_depreciation_lines()
                
                record.message_post(body=_('Đã tạo lại bảng khấu hao'))

    def action_start(self):
        """Bắt đầu khấu hao và tạo các dòng khấu hao"""
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('Chỉ có thể bắt đầu khấu hao từ trạng thái Nháp!'))
            
            # Xóa các dòng cũ nếu có
            record.depreciation_line_ids.unlink()
            
            # Tạo dòng khấu hao
            if record.method == 'linear':
                record._create_linear_depreciation_lines()
            elif record.method == 'declining':
                record._create_declining_depreciation_lines()
            
            record.write({'state': 'running'})
            record.message_post(body=_('Bắt đầu khấu hao tài sản'))

    def action_complete(self):
        """Hoàn thành khấu hao"""
        for record in self:
            record.write({'state': 'completed'})
            record.message_post(body=_('Hoàn thành khấu hao tài sản'))

    def action_cancel(self):
        """Hủy khấu hao"""
        for record in self:
            # Hủy các dòng khấu hao chưa ghi nhận
            record.depreciation_line_ids.filtered(lambda l: l.state == 'draft').write({'state': 'cancelled'})
            record.write({'state': 'cancelled'})
            record.message_post(body=_('Đã hủy khấu hao tài sản'))

    def action_reset_to_draft(self):
        """Reset về nháp"""
        for record in self:
            record.write({'state': 'draft'})
            record.depreciation_line_ids.unlink()

    def _create_linear_depreciation_lines(self):
        """Tạo dòng khấu hao theo phương pháp đường thẳng
        
        Công thức:
        - KH = (NG - GT_TL) / T
        - KH_LK,t = KH × t
        - GT_CL,t = NG - KH_LK,t
        """
        self.ensure_one()
        
        # KH = (NG - GT_TL) / T
        monthly_amount = self.depreciation_value
        date = self.start_date
        
        DepreciationLine = self.env['dnu.asset.depreciation.line']
        
        accumulated = 0.0

        for month in range(1, self.useful_life + 1):
            if month == self.useful_life:
                # Điều chỉnh kỳ cuối để khớp NG - GT_TL
                monthly_amount = (self.depreciation_total - accumulated)

            # KH_LK,t = KH_LK,t-1 + KH_t
            accumulated += monthly_amount
            # GT_CL,t = NG - KH_LK,t
            remaining = self.purchase_value - accumulated

            # Đảm bảo giá trị còn lại không nhỏ hơn giá trị thanh lý
            if remaining < self.salvage_value:
                remaining = self.salvage_value

            DepreciationLine.create({
                'depreciation_id': self.id,
                'date': date,
                'amount': monthly_amount,
                'accumulated_depreciation': accumulated,
                'book_value': remaining,
                'state': 'draft',
            })

            date = date + relativedelta(months=1)

    def _create_declining_depreciation_lines(self):
        """Tạo dòng khấu hao theo phương pháp số dư giảm dần
        
        Công thức:
        - r = 1 - (GT_TL/NG)^(1/T)
        - KH_t = GT_CL,t-1 × r
        - GT_CL,t = NG × (1-r)^t
        - KH_LK,t = NG - GT_CL,t
        """
        self.ensure_one()
        
        # Tính tỷ lệ khấu hao: r = 1 - (GT_TL/NG)^(1/T)
        if self.salvage_value > 0:
            ratio = self.salvage_value / self.purchase_value
            monthly_rate = 1 - pow(ratio, 1.0 / self.useful_life)
        else:
            # Nếu giá trị thanh lý = 0, dùng phương pháp 2/n (theo năm) rồi quy đổi theo tháng
            years = self.useful_life / 12.0
            annual_rate = 2.0 / years if years else 0.0
            monthly_rate = annual_rate / 12.0
        
        remaining_value = self.purchase_value  # GT_CL,0 = NG
        date = self.start_date
        
        DepreciationLine = self.env['dnu.asset.depreciation.line']
        accumulated = 0
        
        for month in range(1, self.useful_life + 1):
            # KH_t = GT_CL,t-1 × r
            monthly_amount = remaining_value * monthly_rate
            
            # Đảm bảo giá trị còn lại không nhỏ hơn giá trị thanh lý
            if remaining_value - monthly_amount < self.salvage_value or month == self.useful_life:
                monthly_amount = remaining_value - self.salvage_value
            
            # Cập nhật giá trị lũy kế và còn lại
            accumulated += monthly_amount
            remaining_value -= monthly_amount
            
            DepreciationLine.create({
                'depreciation_id': self.id,
                'date': date,
                'amount': monthly_amount,
                'accumulated_depreciation': accumulated,
                'book_value': remaining_value,
                'state': 'draft',
            })
            
            date = date + relativedelta(months=1)
            
            # Dừng lại khi đã đạt giá trị thanh lý
            if remaining_value <= self.salvage_value:
                break

    @api.model
    def _cron_compute_depreciation(self):
        """Tính khấu hao tự động hàng tháng"""
        today = fields.Date.today()
        
        depreciations = self.search([
            ('state', '=', 'running'),
            ('end_date', '>=', today),
        ])
        
        for depreciation in depreciations:
            # Tìm các dòng khấu hao đến hạn chưa ghi nhận
            lines_to_post = depreciation.depreciation_line_ids.filtered(
                lambda l: l.state == 'draft' and l.date <= today
            )
            
            for line in lines_to_post:
                line.action_post()
            
            # Kiểm tra xem đã khấu hao hết chưa
            if depreciation.total_depreciated >= depreciation.depreciation_total:
                depreciation.action_complete()


class AssetDepreciationLine(models.Model):
    _name = 'dnu.asset.depreciation.line'
    _description = 'Dòng khấu hao tài sản'
    _order = 'date'

    depreciation_id = fields.Many2one(
        'dnu.asset.depreciation',
        string='Khấu hao',
        required=True,
        ondelete='cascade'
    )
    date = fields.Date(
        string='Ngày',
        required=True
    )
    amount = fields.Float(
        string='Giá trị khấu hao',
        required=True
    )
    accumulated_depreciation = fields.Float(
        string='Khấu hao lũy kế',
        help='Tổng khấu hao từ đầu đến thời điểm này'
    )
    book_value = fields.Float(
        string='Giá trị còn lại',
        help='Giá trị sổ sách sau khi trừ khấu hao'
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('posted', 'Đã ghi nhận'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True)
    
    posted_date = fields.Date(
        string='Ngày ghi nhận',
        readonly=True
    )
    posted_by = fields.Many2one(
        'res.users',
        string='Người ghi nhận',
        readonly=True
    )
    notes = fields.Text(string='Ghi chú')
    
    currency_id = fields.Many2one(
        'res.currency',
        related='depreciation_id.currency_id'
    )

    def action_post(self):
        """Ghi nhận khấu hao"""
        for line in self:
            if line.state != 'draft':
                raise ValidationError(_('Chỉ có thể ghi nhận dòng khấu hao ở trạng thái Nháp!'))
            
            line.write({
                'state': 'posted',
                'posted_date': fields.Date.today(),
                'posted_by': self.env.user.id,
            })

    def action_cancel(self):
        """Hủy ghi nhận"""
        for line in self:
            line.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Reset về nháp"""
        for line in self:
            if line.state == 'posted':
                raise ValidationError(_('Không thể reset dòng đã ghi nhận về nháp!'))
            line.write({'state': 'draft'})
