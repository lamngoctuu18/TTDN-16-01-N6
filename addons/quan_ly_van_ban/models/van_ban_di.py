from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError

class VanBanDi(models.Model):
    _name = 'van_ban_di'
    _description = 'Bảng chứa thông tin văn bản đi'
    _rec_name = 'ten_van_ban'
    _order = 'ngay_gui desc'

    so_van_ban_di = fields.Char("Số hiệu văn bản", required=True)
    ten_van_ban = fields.Char("Tên văn bản", required=True)
    so_hieu_van_ban = fields.Char("Số hiệu văn bản", required=True)
    noi_nhan = fields.Char("Nơi nhận")
    ngay_gui = fields.Date("Ngày gửi", default=fields.Date.today)
    nguoi_gui = fields.Char("Người gửi")
    trang_thai = fields.Selection([
        ('gui', 'Đã gửi'),
        ('dang_xu_ly', 'Đang xử lý'),
        ('hoan_thanh', 'Hoàn thành')
    ], string="Trạng thái", default='gui')
    loai_van_ban_id = fields.Many2one('loai_van_ban', string="Loại văn bản")
    mo_ta = fields.Text("Mô tả")

    _sql_constraints = [
        ('so_van_ban_di_unique', 'unique(so_van_ban_di)', 'Số văn bản đi phải là duy nhất')
    ]

