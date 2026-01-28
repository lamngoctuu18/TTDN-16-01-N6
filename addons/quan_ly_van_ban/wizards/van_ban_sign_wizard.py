# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class VanBanDenSignWizard(models.TransientModel):
    _name = 'van_ban_den.sign.wizard'
    _description = 'Wizard ký văn bản đến'

    van_ban_id = fields.Many2one('van_ban_den', string='Văn bản', required=True, readonly=True)
    signature = fields.Binary(string='Chữ ký', required=True)
    approval_note = fields.Text(string='Ghi chú phê duyệt')
    is_handover_receiver_sign = fields.Boolean(string='Ký bàn giao người nhận', default=False)
    is_handover_director_sign = fields.Boolean(string='Giám đốc ký duyệt bàn giao', default=False)
    
    # Hiển thị thông tin
    ten_van_ban = fields.Char(related='van_ban_id.ten_van_ban', readonly=True)
    request_type = fields.Selection(related='van_ban_id.request_type', readonly=True)
    requester_name = fields.Char(compute='_compute_requester_name', string='Người yêu cầu')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('handover_receiver_sign'):
            res['is_handover_receiver_sign'] = True
        if self.env.context.get('handover_director_sign'):
            res['is_handover_director_sign'] = True
        return res
    
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
        
        # Nếu là ký bàn giao người nhận, cập nhật chữ ký vào biên bản nguồn
        if self.is_handover_receiver_sign or self.env.context.get('handover_receiver_sign'):
            self._update_handover_receiver_signature()
        
        self.van_ban_id.message_post(body='Văn bản đã được KÝ bởi %s' % self.env.user.name)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _update_handover_receiver_signature(self):
        """Cập nhật chữ ký người nhận vào biên bản bàn giao nguồn"""
        van_ban = self.van_ban_id
        if van_ban.source_model == 'dnu.asset.handover' and van_ban.source_res_id:
            try:
                handover = self.env['dnu.asset.handover'].browse(van_ban.source_res_id).exists()
                if handover:
                    handover.write({
                        'receiver_signature': self.signature,
                        'receiver_signature_date': fields.Datetime.now(),
                    })
                    handover.message_post(body='📝 Người nhận %s đã ký biên bản bàn giao' % (
                        handover.nhan_vien_id.ho_va_ten if handover.nhan_vien_id else ''
                    ))
            except Exception as e:
                raise UserError('Lỗi khi cập nhật chữ ký vào biên bản: %s' % str(e))
    
    def action_confirm_receive(self):
        """Người nhận xác nhận nhận tài sản - chỉ ký và cập nhật vào biên bản"""
        self.ensure_one()
        if not self.signature:
            raise UserError('Vui lòng ký tên để xác nhận!')
        
        # Cập nhật chữ ký vào văn bản đến
        self.van_ban_id.write({
            'signature': self.signature,
            'signature_date': fields.Datetime.now(),
        })
        
        # Cập nhật chữ ký người nhận vào biên bản bàn giao nguồn
        self._update_handover_receiver_signature()
        
        self.van_ban_id.message_post(body='✅ Người nhận đã xác nhận nhận tài sản và ký biên bản')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Xác nhận thành công',
                'message': 'Bạn đã ký xác nhận nhận tài sản. Bây giờ hãy bấm nút "Gửi lên Giám đốc" để giám đốc ký duyệt.',
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def action_confirm_director(self):
        """Giám đốc xác nhận ký duyệt bàn giao - tự động điền chữ ký và duyệt biên bản"""
        self.ensure_one()
        if not self.signature:
            raise UserError('Vui lòng ký tên để xác nhận duyệt!')
        
        # Cập nhật chữ ký vào văn bản đến
        self.van_ban_id.write({
            'signature': self.signature,
            'signature_date': fields.Datetime.now(),
        })
        
        # Cập nhật chữ ký giám đốc vào biên bản bàn giao nguồn
        self._update_handover_director_signature()
        
        self.van_ban_id.message_post(body='✅ Giám đốc đã ký duyệt biên bản bàn giao')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ký duyệt thành công',
                'message': 'Bạn đã ký duyệt biên bản bàn giao. Bây giờ hãy bấm nút "Gửi biên bản về người yêu cầu" để hoàn thành.',
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _update_handover_director_signature(self):
        """Cập nhật chữ ký giám đốc vào biên bản bàn giao nguồn"""
        van_ban = self.van_ban_id
        if van_ban.source_model == 'dnu.asset.handover' and van_ban.source_res_id:
            try:
                handover = self.env['dnu.asset.handover'].browse(van_ban.source_res_id).exists()
                if handover:
                    handover.write({
                        'director_signature': self.signature,
                        'director_signature_date': fields.Datetime.now(),
                    })
                    handover.message_post(body='📝 Giám đốc %s đã ký duyệt biên bản bàn giao' % (
                        handover.director_id.ho_va_ten if handover.director_id else ''
                    ))
            except Exception as e:
                raise UserError('Lỗi khi cập nhật chữ ký vào biên bản: %s' % str(e))
    
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
