# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssetSignatureWizard(models.TransientModel):
    """Wizard cho chữ ký điện tử"""
    _name = 'dnu.asset.signature.wizard'
    _description = 'Chữ ký điện tử'

    handover_id = fields.Many2one(
        'dnu.asset.handover',
        string='Biên bản bàn giao',
        required=True
    )
    
    signature_type = fields.Selection([
        ('receiver', 'Người nhận'),
        ('deliverer', 'Người giao'),
    ], string='Loại chữ ký', required=True)
    
    signature = fields.Binary(
        string='Chữ ký',
        required=True,
        help='Vẽ hoặc tải lên chữ ký của bạn'
    )
    
    confirm_text = fields.Char(
        string='Xác nhận',
        help='Nhập "XÁC NHẬN" để xác nhận'
    )
    
    def action_sign(self):
        """Thực hiện ký"""
        self.ensure_one()
        
        if self.confirm_text != 'XÁC NHẬN':
            raise ValidationError(_('Vui lòng nhập "XÁC NHẬN" để xác nhận ký!'))
        
        if not self.signature:
            raise ValidationError(_('Vui lòng tải lên hoặc vẽ chữ ký!'))
        
        # Lưu chữ ký vào biên bản
        if self.signature_type == 'receiver':
            self.handover_id.write({
                'receiver_signature': self.signature,
                'receiver_signature_date': fields.Datetime.now(),
            })
        else:
            self.handover_id.write({
                'deliverer_signature': self.signature,
                'deliverer_signature_date': fields.Datetime.now(),
            })
        
        # Cập nhật trạng thái nếu đã ký đủ
        if self.handover_id.handover_type == 'return':
            # Biên bản trả chỉ cần chữ ký người nhận
            if self.handover_id.receiver_signature:
                self.handover_id.state = 'signed'
        else:
            # Biên bản gán/mượn cần cả hai chữ ký
            if self.handover_id.receiver_signature and self.handover_id.deliverer_signature:
                self.handover_id.state = 'signed'
        
        return {'type': 'ir.actions.act_window_close'}
