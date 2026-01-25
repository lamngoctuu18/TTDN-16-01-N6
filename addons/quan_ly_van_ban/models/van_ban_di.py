from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError

class VanBanDi(models.Model):
    _name = 'van_ban_di'
    _description = 'Bảng chứa thông tin văn bản đi'
    _rec_name = 'ten_van_ban'

    so_van_ban_di = fields.Char("Số văn bản đi", required=True)
    ten_van_ban = fields.Char("Tên văn bản", required=True)
    so_hieu_van_ban = fields.Char("Số hiệu văn bản", required=True)
    noi_nhan = fields.Char("Nơi nhận")

    handler_employee_id = fields.Many2one('nhan_vien', string="Cán bộ xử lý")
    signer_employee_id = fields.Many2one('nhan_vien', string="Người ký")
    receiver_employee_ids = fields.Many2many('nhan_vien', string="Người nhận / phối hợp")
    department_id = fields.Many2one('don_vi', string="Phòng/Ban")

    # Link back to business document (e.g., biên bản tài sản)
    source_model = fields.Char(string='Nguồn (Model)', index=True)
    source_res_id = fields.Integer(string='Nguồn (ID)', index=True)
    is_asset_document = fields.Boolean(
        string='Biên bản tài sản',
        compute='_compute_is_asset_document',
        store=True,
        index=True,
        readonly=True,
        help='Đánh dấu văn bản được tạo từ nghiệp vụ tài sản/phòng họp'
    )

    @api.depends('source_model', 'so_van_ban_di', 'so_hieu_van_ban', 'ten_van_ban')
    def _compute_is_asset_document(self):
        for rec in self:
            by_source = bool(rec.source_model and rec.source_model.startswith('dnu.'))
            so = (rec.so_van_ban_di or rec.so_hieu_van_ban or '').upper()
            by_prefix = so.startswith(('BBG', 'BBM', 'BBTR', 'BBTL'))
            ten = (rec.ten_van_ban or '').strip().lower()
            by_name = ten.startswith('biên bản') or ten.startswith('bien ban')
            rec.is_asset_document = bool(by_source or by_prefix or by_name)

