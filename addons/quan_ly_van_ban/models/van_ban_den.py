from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError

class VanBanDen(models.Model):
    _name = 'van_ban_den'
    _description = 'Bảng chứa thông tin văn bản đến'
    _rec_name = 'ten_van_ban'

    so_van_ban_den = fields.Char("Số hiệu văn bản", required=True)
    ten_van_ban = fields.Char("Tên văn bản", required=True)
    so_hieu_van_ban = fields.Char("Số hiệu văn bản", required=True)
    noi_gui_den = fields.Char("Nơi gửi đến")

    handler_employee_id = fields.Many2one('nhan_vien', string="Cán bộ xử lý")
    signer_employee_id = fields.Many2one('nhan_vien', string="Người ký")
    receiver_employee_ids = fields.Many2many('nhan_vien', 'van_ban_den_receiver_rel', 'van_ban_id', 'employee_id', string="Người nhận / phối hợp")
    department_id = fields.Many2one('don_vi', string="Phòng/Ban")
    due_date = fields.Date(string="Hạn xử lý")

    # Giao việc & nhắc hạn
    task_ids = fields.One2many('van_ban_task', 'van_ban_id', string='Công việc liên quan')
    task_count = fields.Integer(string='Số công việc', compute='_compute_task_count', store=False)
    reminder_enabled = fields.Boolean(string='Bật nhắc hạn', default=True)
    reminder_days = fields.Integer(string='Nhắc trước (ngày)', default=3)
    last_reminder_date = fields.Date(string='Ngày đã nhắc gần nhất')
    is_overdue = fields.Boolean(string='Đã quá hạn', compute='_compute_overdue', store=False)

    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)

    def _compute_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = bool(record.due_date and record.due_date < today)

    def action_create_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Giao việc',
            'res_model': 'van_ban_task',
            'view_mode': 'form',
            'context': {
                'default_van_ban_id': self.id,
                'default_employee_id': self.handler_employee_id.id,
            },
            'target': 'new',
        }

    def action_open_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Công việc liên quan',
            'view_mode': 'tree,form',
            'res_model': 'van_ban_task',
            'domain': [('van_ban_id', '=', self.id)],
            'context': {'default_van_ban_id': self.id},
        }

    @api.model
    def cron_remind_due(self):
        today = fields.Date.today()
        records = self.search([
            ('due_date', '!=', False),
            ('reminder_enabled', '=', True),
            '|', ('last_reminder_date', '=', False), ('last_reminder_date', '!=', today),
        ])
        for rec in records:
            if not rec.handler_employee_id:
                continue
            if not rec.handler_employee_id.user_id:
                continue
            days_left = (rec.due_date - today).days if rec.due_date else None
            if days_left is None:
                continue
            if days_left < 0:
                pass
            if days_left <= rec.reminder_days:
                model_id = self.env['ir.model']._get_id('van_ban_den')
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'res_model_id': model_id,
                    'res_id': rec.id,
                    'user_id': rec.handler_employee_id.user_id.id,
                    'summary': 'Nhắc hạn văn bản',
                    'note': 'Văn bản: %s\nHạn: %s\nCòn %s ngày' % (rec.ten_van_ban, rec.due_date, days_left),
                })
                rec.last_reminder_date = today

