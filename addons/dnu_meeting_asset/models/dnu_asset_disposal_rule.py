# -*- coding: utf-8 -*-

from odoo import fields, models


class AssetDisposalRule(models.Model):
    _name = 'dnu.asset.disposal.rule'
    _description = 'Quy tắc đề xuất giá thanh lý'
    _order = 'sequence asc, id desc'

    name = fields.Char(string='Tên quy tắc', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string='Ưu tiên', default=10)

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
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
    ], string='Lý do thanh lý', required=False,
       help='Để trống nếu áp dụng cho mọi lý do')

    category_id = fields.Many2one(
        'dnu.asset.category',
        string='Danh mục tài sản',
        help='Để trống nếu áp dụng cho mọi danh mục'
    )

    coefficient_percent = fields.Float(
        string='Hệ số (%)',
        default=0.0,
        help='Giá đề xuất = Giá trị hiện tại × (Hệ số/100)'
    )

    min_value = fields.Float(
        string='Giá tối thiểu',
        help='Giá đề xuất tối thiểu (VNĐ). Để trống nếu không giới hạn.'
    )
    max_value = fields.Float(
        string='Giá tối đa',
        help='Giá đề xuất tối đa (VNĐ). Để trống nếu không giới hạn.'
    )

    note = fields.Text(string='Ghi chú')
