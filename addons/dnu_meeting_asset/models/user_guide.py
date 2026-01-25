# -*- coding: utf-8 -*-

from odoo import fields, models


class DnuUserGuide(models.Model):
    _name = 'dnu.user.guide'
    _description = 'Hướng dẫn sử dụng'
    _rec_name = 'name'

    name = fields.Char(string='Tiêu đề', required=True)
    content = fields.Html(string='Nội dung', sanitize=False)
