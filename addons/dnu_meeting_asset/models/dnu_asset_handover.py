# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AssetHandover(models.Model):
    """Biên bản bàn giao tài sản - Chỉ dùng cho mượn và trả"""
    _name = 'dnu.asset.handover'
    _description = 'Biên bản bàn giao tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'handover_date desc'

    name = fields.Char(
        string='Số biên bản',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    
    # Loại biên bản: CHỈ MƯỢN VÀ TRẢ
    handover_type = fields.Selection([
        ('lending', 'Mượn tài sản'),
        ('return', 'Trả tài sản'),
    ], string='Loại biên bản', required=True, default='lending', tracking=True)
    
    # Liên kết với mượn tài sản
    lending_id = fields.Many2one(
        'dnu.asset.lending',
        string='Phiếu mượn',
        ondelete='cascade',
        tracking=True
    )
    
    # Thông tin tài sản
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        tracking=True
    )
    asset_code = fields.Char(related='asset_id.code', string='Mã tài sản', store=True)
    asset_name = fields.Char(related='asset_id.name', string='Tên tài sản', store=True)
    
    # Thông tin nhân viên mượn/trả
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên mượn/trả',
        required=True,
        tracking=True
    )
    don_vi_id = fields.Many2one(
        'don_vi',
        string='Đơn vị',
        related='nhan_vien_id.don_vi_chinh_id',
        store=True
    )
    
    # Người giao (quản lý tài sản)
    deliverer_id = fields.Many2one(
        'nhan_vien',
        string='Người giao/nhận',
        tracking=True,
        help='Người giao tài sản (khi mượn) hoặc người nhận trả (khi trả)'
    )
    
    @api.onchange('asset_id', 'handover_type')
    def _onchange_asset_deliverer(self):
        """Tự động điền người giao là người đang được gán tài sản"""
        if self.asset_id and self.handover_type == 'lending':
            # Tìm người đang được gán tài sản này
            if self.asset_id.assigned_nhan_vien_id:
                self.deliverer_id = self.asset_id.assigned_nhan_vien_id
            else:
                self.deliverer_id = False
    
    # Thông tin bàn giao
    handover_date = fields.Datetime(
        string='Ngày bàn giao',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    expected_return_date = fields.Datetime(
        string='Ngày dự kiến trả',
        help='Chỉ áp dụng cho mượn tài sản'
    )
    
    # Tình trạng tài sản
    condition_handover = fields.Selection([
        ('new', 'Mới'),
        ('good', 'Tốt'),
        ('fair', 'Khá'),
        ('poor', 'Cần sửa chữa'),
    ], string='Tình trạng khi giao', required=True, default='good', tracking=True)
    
    condition_return = fields.Selection([
        ('new', 'Mới'),
        ('good', 'Tốt'),
        ('fair', 'Khá'),
        ('poor', 'Cần sửa chữa'),
        ('damaged', 'Hư hỏng'),
    ], string='Tình trạng khi trả', tracking=True)
    
    accessories = fields.Text(
        string='Phụ kiện đi kèm',
        help='Liệt kê các phụ kiện: sạc, dây cáp, chuột, bàn phím...'
    )
    
    notes = fields.Text(string='Ghi chú')
    
    # ============================================
    # CHỮ KÝ ĐIỆN TỬ - 2 CHỮ KÝ (Người giao + Người nhận)
    # ============================================
    
    # Chữ ký người giao
    deliverer_signature = fields.Binary(
        string='Chữ ký người giao',
        attachment=True,
        tracking=True
    )
    deliverer_signature_date = fields.Datetime(
        string='Ngày ký giao',
        readonly=True
    )
    
    # Chữ ký người nhận (người mượn)
    receiver_signature = fields.Binary(
        string='Chữ ký người nhận',
        attachment=True,
        tracking=True
    )
    receiver_signature_date = fields.Datetime(
        string='Ngày ký nhận',
        readonly=True
    )
    
    # ============================================
    # TRẠNG THÁI
    # ============================================
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending_signature', 'Chờ ký'),
        ('signed', 'Đã ký'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # ============================================
    # TÍCH HỢP VĂN BẢN ĐI
    # ============================================
    van_ban_id = fields.Many2one(
        'van_ban_di',
        string='Văn bản đi',
        help='Văn bản đi chính thức sau khi hoàn thành bàn giao',
        tracking=True
    )

    van_ban_count = fields.Integer(
        string='Số văn bản',
        compute='_compute_van_ban_count',
        store=False
    )
    
    # Tệp đính kèm
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'asset_handover_attachment_rel',
        'handover_id',
        'attachment_id',
        string='Tệp đính kèm'
    )

    def _compute_van_ban_count(self):
        for rec in self:
            rec.van_ban_count = 1 if rec.van_ban_id else 0
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if vals.get('handover_type') == 'lending':
                vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.handover.lending') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.handover.return') or _('New')
        
        return super(AssetHandover, self).create(vals)
    
    # ============================================
    # ACTIONS
    # ============================================
    
    def action_send_for_signature(self):
        """Gửi biên bản để ký"""
        self.ensure_one()
        self.state = 'pending_signature'
        self.message_post(
            body=_('📤 Biên bản đã được gửi để ký.'),
            subject=_('Gửi biên bản'),
        )
    
    def action_sign_receiver(self):
        """Người nhận (người mượn) ký"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Người nhận ký'),
            'res_model': 'dnu.asset.signature.wizard',
            'view_mode': 'form',
            'context': {
                'default_handover_id': self.id,
                'default_signature_type': 'receiver',
            },
            'target': 'new',
        }
    
    def action_sign_deliverer(self):
        """Người giao ký"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Người giao ký'),
            'res_model': 'dnu.asset.signature.wizard',
            'view_mode': 'form',
            'context': {
                'default_handover_id': self.id,
                'default_signature_type': 'deliverer',
            },
            'target': 'new',
        }
    
    def action_complete(self):
        """Hoàn thành biên bản sau khi đủ chữ ký"""
        self.ensure_one()
        
        # Kiểm tra chữ ký
        if self.handover_type == 'return':
            # Biên bản trả chỉ cần 1 chữ ký (người trả)
            if not self.receiver_signature:
                raise ValidationError(_('Biên bản trả cần có chữ ký người trả!'))
        else:
            # Biên bản mượn cần cả 2 chữ ký
            if not self.receiver_signature or not self.deliverer_signature:
                raise ValidationError(_('Biên bản mượn cần có đủ chữ ký của cả 2 bên!'))
        
        self.state = 'completed'
        
        # Tạo văn bản đi
        self._create_van_ban_di()
        
        # Cập nhật phiếu mượn nếu có
        if self.lending_id:
            if self.handover_type == 'lending':
                self.lending_id.write({'state': 'borrowed'})
            elif self.handover_type == 'return':
                self.lending_id.write({
                    'state': 'returned',
                    'actual_return_date': fields.Datetime.now()
                })
        
        self.message_post(
            body=_('✅ Biên bản đã hoàn thành.'),
            subject=_('Hoàn thành biên bản'),
        )
    
    def _create_van_ban_di(self):
        """Tạo văn bản đi sau khi hoàn thành"""
        self.ensure_one()
        
        if self.van_ban_id:
            return self.van_ban_id
        
        type_label = 'mượn' if self.handover_type == 'lending' else 'trả'
        
        VanBanDi = self.env['van_ban_di']
        van_ban = VanBanDi.create({
            'so_van_ban_di': f'BB-{self.name}',
            'ten_van_ban': f'Biên bản {type_label} tài sản - {self.asset_name}',
            'so_hieu_van_ban': self.name,
            'noi_nhan': self.nhan_vien_id.ho_va_ten if self.nhan_vien_id else '',
            'handler_employee_id': self.deliverer_id.id if self.deliverer_id else False,
            'receiver_employee_ids': [(6, 0, [self.nhan_vien_id.id])] if self.nhan_vien_id else False,
            'source_model': self._name,
            'source_res_id': self.id,
        })
        
        self.van_ban_id = van_ban.id
        return van_ban
    
    def action_cancel(self):
        """Hủy biên bản"""
        self.ensure_one()
        self.state = 'cancelled'
        self.message_post(
            body=_('❌ Biên bản đã bị hủy.'),
            subject=_('Hủy biên bản')
        )
    
    def action_open_van_ban(self):
        """Mở văn bản đi"""
        self.ensure_one()
        if not self.van_ban_id:
            raise UserError(_('Chưa có văn bản đi nào.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Văn bản đi'),
            'res_model': 'van_ban_di',
            'res_id': self.van_ban_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_print_handover(self):
        """In biên bản bàn giao"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thông báo'),
                'message': _('Chức năng in biên bản đang được phát triển.'),
                'type': 'warning',
                'sticky': False,
            }
        }
