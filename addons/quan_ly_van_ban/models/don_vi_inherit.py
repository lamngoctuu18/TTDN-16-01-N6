from odoo import models, fields, api

class DonViInherit(models.Model):
    _inherit = 'don_vi'

    vb_den_count = fields.Integer(string='Số VB đến', compute='_compute_vb_den_count', store=False)
    vb_den_overdue_count = fields.Integer(string='VB quá hạn', compute='_compute_vb_den_count', store=False)

    @api.depends()
    def _compute_vb_den_count(self):
        VanBan = self.env['van_ban_den']
        for record in self:
            count_all = VanBan.search_count([('department_id', '=', record.id)])
            count_overdue = VanBan.search_count([
                ('department_id', '=', record.id),
                ('due_date', '!=', False),
                ('due_date', '<', fields.Date.today()),
            ])
            record.vb_den_count = count_all
            record.vb_den_overdue_count = count_overdue

    def action_view_vb_den(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Văn bản đến',
            'view_mode': 'tree,form',
            'res_model': 'van_ban_den',
            'domain': [('department_id', '=', self.id)],
            'context': {'search_default_group_by_department_id': 1},
        }
