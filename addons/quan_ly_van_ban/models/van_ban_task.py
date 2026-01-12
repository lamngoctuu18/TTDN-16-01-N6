from odoo import models, fields, api

class VanBanTask(models.Model):
    _name = 'van_ban_task'
    _description = 'Giao việc cho văn bản'
    _order = 'deadline asc, id desc'

    name = fields.Char(string='Công việc', required=True)
    van_ban_id = fields.Many2one('van_ban_den', string='Văn bản', required=True, ondelete='cascade')
    employee_id = fields.Many2one('nhan_vien', string='Nhân viên phụ trách', required=True)
    deadline = fields.Date(string='Hạn xử lý')
    state = fields.Selection([
        ('todo', 'Chờ xử lý'),
        ('doing', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='todo')
    note = fields.Text(string='Ghi chú')

    def action_mark_done(self):
        for task in self:
            task.state = 'done'
        return True
