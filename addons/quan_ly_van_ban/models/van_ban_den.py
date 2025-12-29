from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError

class VanBanDen(models.Model):
    _name = 'van_ban_den'
    _description = 'Bảng chứa thông tin văn bản đến'
    _rec_name = 'ten_van_ban'
    _order = 'ngay_nhan desc'

    so_van_ban_den = fields.Char("Số hiệu văn bản", required=True)
    ten_van_ban = fields.Char("Tên văn bản", required=True)
    so_hieu_van_ban = fields.Char("Số hiệu văn bản", required=True)
    noi_gui_den = fields.Char("Nơi gửi đến")
    ngay_nhan = fields.Date("Ngày nhận", default=fields.Date.today)
    nguoi_nhan = fields.Char("Người nhận")
    trang_thai = fields.Selection([
        ('nhan', 'Đã nhận'),
        ('dang_xu_ly', 'Đang xử lý'),
        ('hoan_thanh', 'Hoàn thành')
    ], string="Trạng thái", default='nhan')
    loai_van_ban_id = fields.Many2one('loai_van_ban', string="Loại văn bản")
    mo_ta = fields.Text("Mô tả")

    _sql_constraints = [
        ('so_van_ban_den_unique', 'unique(so_van_ban_den)', 'Số văn bản đến phải là duy nhất')
    ]

