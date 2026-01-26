# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VanBanDen(models.Model):
    _inherit = 'van_ban_den'

    processing_email_sent_date = fields.Date(string='Ngày đã gửi email xử lý')
    last_processing_handler_id = fields.Many2one(
        'nhan_vien',
        string='Người xử lý đã được thông báo'
    )
    email_send_count = fields.Integer(string='Số lần gửi email', default=0)

    meeting_room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng họp',
        compute='_compute_meeting_links',
        store=True,
        index=True,
        readonly=True,
    )
    meeting_booking_id = fields.Many2one(
        'dnu.meeting.booking',
        string='Booking phòng họp',
        compute='_compute_meeting_links',
        store=True,
        index=True,
        readonly=True,
    )

    @api.depends('source_model', 'source_res_id')
    def _compute_meeting_links(self):
        Room = self.env['dnu.meeting.room']
        Booking = self.env['dnu.meeting.booking']
        for rec in self:
            rec.meeting_room_id = False
            rec.meeting_booking_id = False

            if rec.source_model == 'dnu.meeting.room' and rec.source_res_id:
                rec.meeting_room_id = Room.browse(rec.source_res_id).exists()
            elif rec.source_model == 'dnu.meeting.booking' and rec.source_res_id:
                rec.meeting_booking_id = Booking.browse(rec.source_res_id).exists()

    def _get_handler_email(self):
        self.ensure_one()
        handler = self.handler_employee_id
        if not handler:
            return False
        if handler.email:
            return handler.email
        if getattr(handler, 'user_id', False) and handler.user_id.email:
            return handler.user_id.email
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

    def _create_processing_activity(self):
        self.ensure_one()
        handler = self.handler_employee_id
        if not handler or not getattr(handler, 'user_id', False):
            return False
        model_id = self.env['ir.model']._get_id('van_ban_den')
        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': model_id,
            'res_id': self.id,
            'user_id': handler.user_id.id,
            'summary': 'Văn bản đến cần xử lý',
            'note': 'Văn bản "%s" cần xử lý. Hạn xử lý: %s.' % (
                self.ten_van_ban,
                self.due_date or 'N/A',
            ),
        })
        return True

    def _send_processing_email(self):
        """Gửi email thông báo văn bản cần xử lý cho người xử lý và admin"""
        template = self.env.ref('dnu_meeting_asset.email_template_van_ban_den_processing', raise_if_not_found=False)
        if not template:
            _logger.warning('Template email_template_van_ban_den_processing not found')
            return
        
        for rec in self:
            recipients = []
            
            # Email người xử lý
            handler_email = rec._get_handler_email()
            if handler_email:
                recipients.append(handler_email)
            
            # Email admin
            admin_emails = rec._get_admin_emails()
            for email in admin_emails:
                if email not in recipients:
                    recipients.append(email)
            
            if not recipients:
                _logger.warning(f'No recipients for van_ban_den {rec.id}')
                continue
            
            sent_count = 0
            for email in recipients:
                try:
                    template.send_mail(rec.id, force_send=True, email_values={
                        'email_to': email,
                    })
                    sent_count += 1
                    _logger.info(f'Sent processing email to {email} for van_ban_den {rec.id}')
                except Exception as e:
                    _logger.error(f'Error sending email to {email}: {str(e)}')
            
            if sent_count > 0:
                rec._create_processing_activity()
                rec.write({
                    'processing_email_sent_date': fields.Date.today(),
                    'last_processing_handler_id': rec.handler_employee_id.id if rec.handler_employee_id else False,
                    'email_send_count': rec.email_send_count + 1,
                })

    @api.model
    def create(self, vals):
        record = super(VanBanDen, self).create(vals)
        if record.handler_employee_id:
            record._send_processing_email()
        return record

    def write(self, vals):
        old_handler_by_id = {rec.id: rec.handler_employee_id.id for rec in self}
        result = super(VanBanDen, self).write(vals)
        if 'handler_employee_id' in vals:
            for rec in self:
                old_handler = old_handler_by_id.get(rec.id)
                if rec.handler_employee_id and rec.handler_employee_id.id != old_handler:
                    rec._send_processing_email()
        else:
            for rec in self:
                if rec.handler_employee_id and not rec.processing_email_sent_date:
                    rec._send_processing_email()
        return result
