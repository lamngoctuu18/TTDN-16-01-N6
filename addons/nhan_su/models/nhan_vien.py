from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'
    _rec_name = 'ho_va_ten'
    _order = 'ten asc, tuoi desc'

    ma_dinh_danh = fields.Char("Mã định danh", required=True)

    ho_ten_dem = fields.Char("Họ tên đệm", required=True)
    ten = fields.Char("Tên", required=True)
    ho_va_ten = fields.Char("Họ và tên", compute="_compute_ho_va_ten", store=True)
    
    ngay_sinh = fields.Date("Ngày sinh")
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    so_dien_thoai = fields.Char("Số điện thoại")
    lich_su_cong_tac_ids = fields.One2many(
        "lich_su_cong_tac", 
        inverse_name="nhan_vien_id", 
        string = "Danh sách lịch sử công tác")
    tuoi = fields.Integer("Tuổi", compute="_compute_tuoi", store=True)
    anh = fields.Binary("Ảnh")
    danh_sach_chung_chi_bang_cap_ids = fields.One2many(
        "danh_sach_chung_chi_bang_cap", 
        inverse_name="nhan_vien_id", 
        string = "Danh sách chứng chỉ bằng cấp")
    so_nguoi_bang_tuoi = fields.Integer("Số người bằng tuổi",
                                        compute="_compute_so_nguoi_bang_tuoi",
                                        store=True
                                        )
    
    # Chức vụ và đơn vị hiện tại (từ lịch sử công tác loại "Chính")
    don_vi_chinh_id = fields.Many2one(
        'don_vi',
        string='Phòng ban',
        compute='_compute_chuc_vu_don_vi_chinh',
        store=True,
        help='Đơn vị/Phòng ban chính hiện tại'
    )
    chuc_vu_chinh_id = fields.Many2one(
        'chuc_vu',
        string='Chức vụ',
        compute='_compute_chuc_vu_don_vi_chinh',
        store=True,
        help='Chức vụ chính hiện tại'
    )
    
    @api.depends('lich_su_cong_tac_ids', 'lich_su_cong_tac_ids.loai_chuc_vu', 
                 'lich_su_cong_tac_ids.chuc_vu_id', 'lich_su_cong_tac_ids.don_vi_id')
    def _compute_chuc_vu_don_vi_chinh(self):
        """Tự động lấy chức vụ và đơn vị chính từ lịch sử công tác"""
        for record in self:
            # Tìm bản ghi lịch sử công tác có loại chức vụ = "Chính"
            lich_su_chinh = record.lich_su_cong_tac_ids.filtered(
                lambda x: x.loai_chuc_vu == 'Chính'
            )
            if lich_su_chinh:
                # Lấy bản ghi đầu tiên (có thể sắp xếp theo ngày nếu có)
                record.don_vi_chinh_id = lich_su_chinh[0].don_vi_id
                record.chuc_vu_chinh_id = lich_su_chinh[0].chuc_vu_id
            else:
                record.don_vi_chinh_id = False
                record.chuc_vu_chinh_id = False
    
    @api.depends("tuoi")
    def _compute_so_nguoi_bang_tuoi(self):
        for record in self:
            if record.tuoi:
                records = self.env['nhan_vien'].search([
                    ('tuoi', '=', record.tuoi),
                    ('ma_dinh_danh', '!=', record.ma_dinh_danh)
                ])
                record.so_nguoi_bang_tuoi = len(records)
            else:
                record.so_nguoi_bang_tuoi = 0
    _sql_constraints = [
        ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', 'Mã định danh phải là duy nhất')
    ]

    @api.depends("ho_ten_dem", "ten")
    def _compute_ho_va_ten(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                record.ho_va_ten = record.ho_ten_dem + ' ' + record.ten
    
    
    
                
    @api.onchange("ten", "ho_ten_dem")
    def _default_ma_dinh_danh(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                chu_cai_dau = ''.join([tu[0][0] for tu in record.ho_ten_dem.lower().split()])
                record.ma_dinh_danh = record.ten.lower() + chu_cai_dau
    
    @api.depends("ngay_sinh")
    def _compute_tuoi(self):
        for record in self:
            if record.ngay_sinh:
                year_now = date.today().year
                record.tuoi = year_now - record.ngay_sinh.year

    @api.constrains('tuoi')
    def _check_tuoi(self):
        for record in self:
            if record.tuoi < 18:
                raise ValidationError("Tuổi không được bé hơn 18")
