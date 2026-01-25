from odoo import models, fields, api

class NhanVienInherit(models.Model):
    _inherit = 'nhan_vien'

    # Văn bản đến
    van_ban_den_ids = fields.One2many('van_ban_den', 'handler_employee_id', string="Văn bản đến xử lý")
    van_ban_ky_ids = fields.One2many('van_ban_den', 'signer_employee_id', string="Văn bản đến đã ký")
    van_ban_nhan_ids = fields.Many2many('van_ban_den', 'van_ban_den_receiver_rel', 'employee_id', 'van_ban_id', string="Văn bản đến nhận/phối hợp")
    van_ban_den_count = fields.Integer(compute='_compute_van_ban_den_count', string="Số văn bản đến", store=True)

    # Văn bản đi
    van_ban_di_xu_ly_ids = fields.One2many('van_ban_di', 'handler_employee_id', string="Văn bản đi xử lý")
    van_ban_di_ky_ids = fields.One2many('van_ban_di', 'signer_employee_id', string="Văn bản đi đã ký")
    van_ban_di_nhan_ids = fields.Many2many('van_ban_di', string="Văn bản đi nhận/phối hợp")
    van_ban_di_count = fields.Integer(compute='_compute_van_ban_di_count', string="Số văn bản đi", store=True)

    @api.depends('van_ban_den_ids')
    def _compute_van_ban_den_count(self):
        for record in self:
            record.van_ban_den_count = len(record.van_ban_den_ids)

    @api.depends('van_ban_di_xu_ly_ids', 'van_ban_di_ky_ids', 'van_ban_di_nhan_ids')
    def _compute_van_ban_di_count(self):
        for record in self:
            # Count unique van_ban_di records
            all_ids = set()
            all_ids.update(record.van_ban_di_xu_ly_ids.ids)
            all_ids.update(record.van_ban_di_ky_ids.ids)
            all_ids.update(record.van_ban_di_nhan_ids.ids)
            record.van_ban_di_count = len(all_ids)

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

    def action_view_van_ban_di(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Văn bản đi',
            'view_mode': 'tree,form',
            'res_model': 'van_ban_di',
            'domain': ['|', '|',
                      ('handler_employee_id', '=', self.id),
                      ('signer_employee_id', '=', self.id),
                      ('receiver_employee_ids', 'in', self.id)],
            'context': {'default_handler_employee_id': self.id},
        }
