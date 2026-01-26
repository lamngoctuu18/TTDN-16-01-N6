# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VanBanTask(models.Model):
    _inherit = 'van_ban_task'

    due_email_sent_date = fields.Date(string='Ngày đã gửi nhắc đến hạn')
    overdue_email_sent_date = fields.Date(string='Ngày đã gửi nhắc quá hạn')
    email_send_count = fields.Integer(string='Số lần gửi email', default=0)

    def _get_employee_email(self):
        self.ensure_one()
        employee = self.employee_id
        if not employee:
            return False
        if employee.email:
            return employee.email
        if getattr(employee, 'user_id', False) and employee.user_id.email:
            return employee.user_id.email
        return False

    def _get_admin_emails(self):
        """Lấy danh sách email admin để CC"""
        admin_emails = []
        admin_email_param = self.env['ir.config_parameter'].sudo().get_param('dnu_meeting_asset.admin_notification_email')
        if admin_email_param:
            admin_emails.extend([e.strip() for e in admin_email_param.split(',') if e.strip()])
        admin_users = self.env['res.users'].sudo().search([('groups_id', 'in', self.env.ref('base.group_system').id)])
        for user in admin_users:
            if user.email and user.email not in admin_emails:
                admin_emails.append(user.email)
        return admin_emails

    def _send_task_email(self, template_xmlid, email_to=None, include_admin=True):
        """Gửi email và tracking"""
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning(f'Template {template_xmlid} not found')
            return False
        
        recipients = []
        
        # Email nhân viên
        employee_email = email_to or self._get_employee_email()
        if employee_email:
            recipients.append(employee_email)
        
        # Email admin
        if include_admin:
            admin_emails = self._get_admin_emails()
            for email in admin_emails:
                if email not in recipients:
                    recipients.append(email)
        
        if not recipients:
            _logger.warning(f'No recipients for task {self.id}')
            return False
        
        sent_count = 0
        for email in recipients:
            try:
                template.send_mail(self.id, force_send=True, email_values={
                    'email_to': email,
                })
                sent_count += 1
                _logger.info(f'Sent task email to {email} for task {self.id}')
            except Exception as e:
                _logger.error(f'Error sending email to {email}: {str(e)}')
        
        if sent_count > 0:
            self.email_send_count += 1
        
        return sent_count > 0

    def _create_task_activity(self, summary, note):
        self.ensure_one()
        if not self.employee_id or not getattr(self.employee_id, 'user_id', False):
            return False
        model_id = self.env['ir.model']._get_id('van_ban_task')
        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': model_id,
            'res_id': self.id,
            'user_id': self.employee_id.user_id.id,
            'summary': summary,
            'note': note,
        })
        return True

    @api.model
    def _cron_send_task_deadline_notifications(self):
        today = fields.Date.today()
        # Due today
        due_tasks = self.search([
            ('state', '!=', 'done'),
            ('deadline', '=', today),
        ])
        for task in due_tasks:
            if task.due_email_sent_date == today:
                continue
            sent = task._send_task_email('dnu_meeting_asset.email_template_van_ban_task_due')
            if sent:
                task._create_task_activity(
                    summary='Công việc đến hạn',
                    note='Công việc "%s" đến hạn hôm nay (%s).' % (task.name, task.deadline),
                )
                task.due_email_sent_date = today

        # Overdue
        overdue_tasks = self.search([
            ('state', '!=', 'done'),
            ('deadline', '!=', False),
            ('deadline', '<', today),
        ])
        for task in overdue_tasks:
            if task.overdue_email_sent_date == today:
                continue
            sent = task._send_task_email('dnu_meeting_asset.email_template_van_ban_task_overdue')
            if sent:
                task._create_task_activity(
                    summary='Công việc quá hạn',
                    note='Công việc "%s" đã quá hạn từ %s.' % (task.name, task.deadline),
                )
                task.overdue_email_sent_date = today
