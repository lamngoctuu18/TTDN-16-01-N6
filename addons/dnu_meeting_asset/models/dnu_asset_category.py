# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AssetCategory(models.Model):
    _name = 'dnu.asset.category'
    _description = 'Danh mục tài sản'
    _order = 'name'

    name = fields.Char(string='Tên danh mục', required=True, translate=True)
    code = fields.Char(string='Mã danh mục')
    description = fields.Text(string='Mô tả')
    parent_id = fields.Many2one(
        'dnu.asset.category',
        string='Danh mục cha',
        ondelete='cascade',
        index=True
    )
    child_ids = fields.One2many(
        'dnu.asset.category',
        'parent_id',
        string='Danh mục con'
    )
    asset_ids = fields.One2many(
        'dnu.asset',
        'category_id',
        string='Tài sản'
    )
    asset_count = fields.Integer(
        string='Số lượng tài sản',
        compute='_compute_asset_count',
        store=True
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for category in self:
            category.asset_count = len(category.asset_ids)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã danh mục phải là duy nhất!')
    ]
