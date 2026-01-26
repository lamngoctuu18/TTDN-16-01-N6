# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class VanBanDenSignWizard(models.TransientModel):
    _name = 'van_ban_den.sign.wizard'
    _description = 'Wizard ký văn bản đến'

    van_ban_id = fields.Many2one('van_ban_den', string='Văn bản', required=True, readonly=True)
    signature = fields.Binary(string='Chữ ký', required=True)
    approval_note = fields.Text(string='Ghi chú phê duyệt')
    
    # Hiển thị thông tin
    ten_van_ban = fields.Char(related='van_ban_id.ten_van_ban', readonly=True)
    request_type = fields.Selection(related='van_ban_id.request_type', readonly=True)
    requester_name = fields.Char(compute='_compute_requester_name', string='Người yêu cầu')
    
    @api.depends('van_ban_id.requester_id')
    def _compute_requester_name(self):
        for rec in self:
            rec.requester_name = rec.van_ban_id.requester_id.ho_va_ten if rec.van_ban_id.requester_id else ''
    
    def action_sign(self):
        """Chỉ ký văn bản (không duyệt)"""
        self.ensure_one()
        if not self.signature:
            raise UserError('Vui lòng ký tên!')
        
        self.van_ban_id.write({
            'signature': self.signature,
            'signature_date': fields.Datetime.now(),
        })
        
        self.van_ban_id.message_post(body='Văn bản đã được KÝ bởi %s' % self.env.user.name)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_sign_and_approve(self):
        """Ký và duyệt cùng lúc"""
        self.ensure_one()
        if not self.signature:
            raise UserError('Vui lòng ký tên!')
        
        # Cập nhật chữ ký và ghi chú
        self.van_ban_id.write({
            'signature': self.signature,
            'signature_date': fields.Datetime.now(),
            'approval_note': self.approval_note,
        })
        
        # Gọi action_approve với context để bypass check signature
        self.van_ban_id.with_context(from_sign_wizard=True).action_approve()
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_sign_and_reject(self):
        """Ký và từ chối"""
        self.ensure_one()
        if not self.signature:
            raise UserError('Vui lòng ký tên!')
        
        # Cập nhật chữ ký và ghi chú
        self.van_ban_id.write({
            'signature': self.signature,
            'signature_date': fields.Datetime.now(),
            'approval_note': self.approval_note,
        })
        
        # Gọi action_reject
        self.van_ban_id.action_reject()
        
        return {'type': 'ir.actions.act_window_close'}
