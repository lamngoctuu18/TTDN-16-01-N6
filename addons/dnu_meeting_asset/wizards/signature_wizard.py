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
        
        # Lưu chữ ký vào biên bản theo loại
        if self.signature_type == 'receiver':
            self.handover_id.write({
                'receiver_signature': self.signature,
                'receiver_signature_date': fields.Datetime.now(),
            })
            self.handover_id.message_post(
                body=_('✅ Người nhận %s đã ký biên bản.') % (
                    self.handover_id.nhan_vien_id.ho_va_ten if self.handover_id.nhan_vien_id else ''
                ),
                subject=_('Người nhận ký'),
            )
        elif self.signature_type == 'deliverer':
            self.handover_id.write({
                'deliverer_signature': self.signature,
                'deliverer_signature_date': fields.Datetime.now(),
            })
            self.handover_id.message_post(
                body=_('✅ Người giao %s đã ký biên bản.') % (
                    self.handover_id.deliverer_id.ho_va_ten if self.handover_id.deliverer_id else ''
                ),
                subject=_('Người giao ký'),
            )
        
        # Kiểm tra nếu đủ chữ ký thì chuyển sang trạng thái signed
        handover = self.handover_id
        if handover.handover_type == 'return':
            if handover.receiver_signature:
                handover.state = 'signed'
        else:
            if handover.receiver_signature and handover.deliverer_signature:
                handover.state = 'signed'
        
        return {'type': 'ir.actions.act_window_close'}
