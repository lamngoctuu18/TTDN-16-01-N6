from odoo import models, fields, api

class NhanVienInherit(models.Model):
    _inherit = 'nhan_vien'

    van_ban_den_ids = fields.One2many('van_ban_den', 'handler_employee_id', string="Văn bản đến xử lý")
    van_ban_ky_ids = fields.One2many('van_ban_den', 'signer_employee_id', string="Văn bản đã ký")
    van_ban_nhan_ids = fields.Many2many('van_ban_den', 'van_ban_den_receiver_rel', 'employee_id', 'van_ban_id', string="Văn bản nhận/phối hợp")
    van_ban_den_count = fields.Integer(compute='_compute_van_ban_den_count', string="Số văn bản đến", store=True)

    @api.depends('van_ban_den_ids')
    def _compute_van_ban_den_count(self):
        for record in self:
            record.van_ban_den_count = len(record.van_ban_den_ids)

    def action_view_van_ban_den(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Văn bản đến',
            'view_mode': 'tree,form',
            'res_model': 'van_ban_den',
            'domain': [('handler_employee_id', '=', self.id)],
            'context': {'default_handler_employee_id': self.id},
        }
