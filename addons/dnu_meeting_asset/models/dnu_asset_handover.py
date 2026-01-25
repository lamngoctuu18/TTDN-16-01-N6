# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64


class AssetHandover(models.Model):
    """Biên bản bàn giao tài sản"""
    _name = 'dnu.asset.handover'
    _description = 'Biên bản bàn giao tài sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'handover_date desc'

    name = fields.Char(
        string='Số biên bản',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    
    handover_type = fields.Selection([
        ('assignment', 'Gán tài sản'),
        ('lending', 'Mượn tài sản'),
        ('return', 'Trả tài sản'),
    ], string='Loại biên bản', required=True, default='assignment', tracking=True)
    
    # Liên kết với gán/mượn tài sản
    assignment_id = fields.Many2one(
        'dnu.asset.assignment',
        string='Phiếu gán',
        ondelete='cascade',
        tracking=True
    )
    lending_id = fields.Many2one(
        'dnu.asset.lending',
        string='Phiếu mượn',
        ondelete='cascade',
        tracking=True
    )
    
    # Thông tin tài sản
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        tracking=True
    )
    asset_code = fields.Char(related='asset_id.code', string='Mã tài sản', store=True)
    asset_name = fields.Char(related='asset_id.name', string='Tên tài sản', store=True)
    
    # Thông tin nhân viên nhận
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên nhận',
        required=True,
        tracking=True
    )
    don_vi_id = fields.Many2one(
        'don_vi',
        string='Đơn vị',
        related='nhan_vien_id.don_vi_chinh_id',
        store=True
    )
    
    # Thông tin bàn giao
    handover_date = fields.Datetime(
        string='Ngày bàn giao',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    expected_return_date = fields.Datetime(
        string='Ngày dự kiến trả',
        help='Chỉ áp dụng cho mượn tài sản'
    )
    
    # Tình trạng tài sản
    condition_handover = fields.Selection([
        ('new', 'Mới'),
        ('good', 'Tốt'),
        ('fair', 'Khá'),
        ('poor', 'Cần sửa chữa'),
    ], string='Tình trạng khi giao', required=True, default='good', tracking=True)
    
    condition_return = fields.Selection([
        ('new', 'Mới'),
        ('good', 'Tốt'),
        ('fair', 'Khá'),
        ('poor', 'Cần sửa chữa'),
        ('damaged', 'Hư hỏng'),
    ], string='Tình trạng khi trả', tracking=True)
    
    accessories = fields.Text(
        string='Phụ kiện đi kèm',
        help='Liệt kê các phụ kiện: sạc, dây cáp, chuột, bàn phím...'
    )
    
    notes = fields.Text(string='Ghi chú')
    
    # Chữ ký điện tử
    receiver_signature = fields.Binary(
        string='Chữ ký người nhận',
        attachment=True,
        tracking=True
    )
    receiver_signature_date = fields.Datetime(
        string='Ngày ký nhận',
        readonly=True
    )
    
    deliverer_signature = fields.Binary(
        string='Chữ ký người giao',
        attachment=True,
        tracking=True
    )
    deliverer_signature_date = fields.Datetime(
        string='Ngày ký giao',
        readonly=True
    )
    deliverer_id = fields.Many2one(
        'nhan_vien',
        string='Người giao',
        default=lambda self: self.env.user.nhan_vien_id if hasattr(self.env.user, 'nhan_vien_id') else False
    )
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending_signature', 'Chờ ký'),
        ('signed', 'Đã ký'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # Tích hợp văn bản
    van_ban_id = fields.Many2one(
        'van_ban_di',
        string='Văn bản liên quan',
        help='Văn bản chính thức về việc bàn giao tài sản',
        tracking=True
    )

    van_ban_count = fields.Integer(
        string='Số văn bản',
        compute='_compute_van_ban_count',
        store=False
    )

    def _compute_van_ban_count(self):
        for rec in self:
            rec.van_ban_count = 1 if rec.van_ban_id else 0
    
    # Tệp đính kèm
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'asset_handover_attachment_rel',
        'handover_id',
        'attachment_id',
        string='Tệp đính kèm'
    )

    def _get_notification_employees(self, event):
        """Return nhan_vien recipients for a given notification event."""
        self.ensure_one()

        employees = self.env['nhan_vien']

        if event == 'pending_signature':
            if self.nhan_vien_id and not self.receiver_signature:
                employees |= self.nhan_vien_id
            if self.handover_type != 'return' and self.deliverer_id and not self.deliverer_signature:
                employees |= self.deliverer_id
        else:
            if self.nhan_vien_id:
                employees |= self.nhan_vien_id
            if self.deliverer_id:
                employees |= self.deliverer_id

        return employees

    def _get_notification_users(self, event):
        """Resolve res.users recipients from nhan_vien via hr.employee.user_id or email lookup."""
        self.ensure_one()

        Users = self.env['res.users']
        employees = self._get_notification_employees(event)

        for nv in employees:
            user = False
            if getattr(nv, 'hr_employee_id', False) and nv.hr_employee_id and nv.hr_employee_id.user_id:
                user = nv.hr_employee_id.user_id

            if not user:
                email = (nv.email or (nv.hr_employee_id.work_email if nv.hr_employee_id else False) or '').strip()
                if email:
                    user = self.env['res.users'].search([
                        '|',
                        ('login', '=', email),
                        ('partner_id.email', '=', email),
                    ], limit=1)

            if user:
                Users |= user

        return Users

    def _get_notification_email_to(self, event):
        """Comma-separated email recipients for mail templates."""
        self.ensure_one()

        emails = []
        for nv in self._get_notification_employees(event):
            email = (nv.email or (nv.hr_employee_id.work_email if nv.hr_employee_id else False) or '').strip()
            if email and email not in emails:
                emails.append(email)

        return ','.join(emails)

    def _schedule_notification_activities(self, event, summary, note):
        """Create a TODO activity for each resolved user (deduplicated)."""
        self.ensure_one()

        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return

        users = self._get_notification_users(event)
        if not users:
            return

        Activity = self.env['mail.activity']
        for user in users:
            exists = Activity.search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', '=', summary),
                ('state', '=', 'planned'),
            ], limit=1)
            if exists:
                continue
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=user.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today(),
            )

    def _send_template_notification(self, template_xmlid, event):
        """Send email via a template (force_send). Skips if no recipients."""
        self.ensure_one()

        if not self._get_notification_email_to(event):
            return

        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _notify_event(self, event):
        """Notify signers/participants via Inbox activities + email."""
        self.ensure_one()

        base_url = self.get_base_url()
        record_url = f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"
        asset_label = self.asset_name or (self.asset_id.name if self.asset_id else '')

        if event == 'pending_signature':
            summary = _('Cần ký biên bản %s') % (self.name or '')
            note = _('Biên bản bàn giao cần chữ ký.\n\nTài sản: %s\nLink: %s') % (
                asset_label or 'N/A',
                record_url,
            )
            self._schedule_notification_activities(event, summary, note)
            self._send_template_notification('dnu_meeting_asset.email_template_handover_signature', event)
            return

        if event == 'signed':
            summary = _('Biên bản %s đã ký') % (self.name or '')
            note = _('Biên bản bàn giao đã được ký đầy đủ.\n\nTài sản: %s\nLink: %s') % (
                asset_label or 'N/A',
                record_url,
            )
            self._schedule_notification_activities(event, summary, note)
            self._send_template_notification('dnu_meeting_asset.email_template_handover_signed', event)
            return

        if event == 'completed':
            summary = _('Biên bản %s đã hoàn thành') % (self.name or '')
            note = _('Biên bản bàn giao đã hoàn thành.\n\nTài sản: %s\nLink: %s') % (
                asset_label or 'N/A',
                record_url,
            )
            self._schedule_notification_activities(event, summary, note)
            self._send_template_notification('dnu_meeting_asset.email_template_handover_completed', event)
            return

    def write(self, vals):
        old_states = {rec.id: rec.state for rec in self}
        res = super().write(vals)

        if 'state' in vals:
            for rec in self:
                old = old_states.get(rec.id)
                new = rec.state
                if old != new and new in ('signed', 'completed'):
                    rec._notify_event(new)

        return res
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if vals.get('handover_type') == 'assignment':
                vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.handover.assignment') or _('New')
            elif vals.get('handover_type') == 'lending':
                vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.handover.lending') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.handover.return') or _('New')
        return super(AssetHandover, self).create(vals)
    
    @api.onchange('asset_id', 'lending_id')
    def _onchange_asset_id(self):
        """Tự động load người giao và người nhận theo loại biên bản"""
        if self.asset_id:
            # Tìm người hiện đang được gán tài sản (chủ tài sản)
            current_assignment = self.env['dnu.asset.assignment'].search([
                ('asset_id', '=', self.asset_id.id),
                ('date_to', '=', False),
                ('state', '=', 'active')  # Đổi từ 'assigned' thành 'active'
            ], limit=1)
            
            asset_owner = None
            if current_assignment and current_assignment.nhan_vien_id:
                asset_owner = current_assignment.nhan_vien_id
            elif self.asset_id.assigned_nhan_vien_id:
                asset_owner = self.asset_id.assigned_nhan_vien_id
            
            # Tìm người đang mượn tài sản (nếu có)
            current_lending = self.env['dnu.asset.lending'].search([
                ('asset_id', '=', self.asset_id.id),
                ('state', 'in', ['approved', 'borrowed']),
                ('date_expected_return', '>=', fields.Datetime.now())
            ], limit=1)
            
            current_borrower = current_lending.nhan_vien_muon_id if current_lending else None
            
            # Logic theo loại biên bản
            if self.handover_type == 'return':
                # BIÊN BẢN TRẢ: Người mượn giao lại cho người đã giao trong biên bản mượn
                lending_deliverer = None
                lending_borrower = None
                if self.lending_id:
                    lending_borrower = self.lending_id.nhan_vien_muon_id
                    if self.lending_id.handover_id:
                        lending_deliverer = self.lending_id.handover_id.deliverer_id

                # Theo yêu cầu: không dùng người giao ở biên bản trả
                self.deliverer_id = False
                # Người nhận = người bàn giao lại
                self.nhan_vien_id = lending_borrower or current_borrower
            elif self.handover_type == 'assignment':
                # BIÊN BẢN GÁN: ưu tiên Giám đốc/Phó Giám đốc thuộc Ban Giám Đốc làm người giao
                # Tìm trực tiếp nhân viên có chức vụ chứa "giám đốc" và phòng ban chứa "giám đốc"
                deliverer_director = self.env['nhan_vien'].search([
                    ('don_vi_chinh_id.ten_don_vi', 'ilike', 'giám đốc'),
                    '|',
                    ('chuc_vu_chinh_id.ten_chuc_vu', '=ilike', 'giám đốc'),
                    ('chuc_vu_chinh_id.ten_chuc_vu', 'ilike', 'phó%giám đốc'),
                ], order='chuc_vu_chinh_id asc', limit=1)
                self.deliverer_id = deliverer_director or asset_owner
            else:
                # BIÊN BẢN MƯỢN: người giao là người đang được gán tài sản
                self.deliverer_id = asset_owner
                # Người nhận để trống, user sẽ chọn
    
    @api.onchange('handover_type')
    def _onchange_handover_type(self):
        """Khi đổi loại biên bản, cập nhật lại người giao/nhận"""
        if self.asset_id:
            self._onchange_asset_id()
    
    def action_send_for_signature(self):
        """Gửi để ký"""
        self.ensure_one()
        self.state = 'pending_signature'
        # Notify via activities + email
        self._notify_event('pending_signature')
        
    def action_sign_receiver(self):
        """Người nhận ký"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ký nhận tài sản',
            'res_model': 'dnu.asset.signature.wizard',
            'view_mode': 'form',
            'context': {
                'default_handover_id': self.id,
                'default_signature_type': 'receiver',
            },
            'target': 'new',
        }
    
    def action_sign_deliverer(self):
        """Người giao ký"""
        self.ensure_one()
        if self.handover_type == 'return':
            raise ValidationError(_('Biên bản trả chỉ yêu cầu người bàn giao lại ký.'))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ký giao tài sản',
            'res_model': 'dnu.asset.signature.wizard',
            'view_mode': 'form',
            'context': {
                'default_handover_id': self.id,
                'default_signature_type': 'deliverer',
            },
            'target': 'new',
        }
    
    def action_complete(self):
        """Hoàn thành biên bản"""
        self.ensure_one()
        if self.handover_type == 'return':
            if not self.receiver_signature:
                raise ValidationError(_('Biên bản trả chỉ cần chữ ký của người bàn giao lại.'))
        else:
            if not self.receiver_signature or not self.deliverer_signature:
                raise ValidationError(_('Cần có đầy đủ chữ ký của cả hai bên!'))

        if self.state != 'signed':
            raise ValidationError(_('Biên bản phải ở trạng thái "Đã ký" trước khi Hoàn thành.'))

        self.state = 'completed'
        
        # Nếu là biên bản TRẢ -> tự động gán tài sản cho người nhận
        if self.handover_type == 'return' and self.nhan_vien_id and self.asset_id:
            self._auto_assign_asset_after_return()
        
        # Tạo văn bản chính thức nếu chưa có
        if not self.van_ban_id:
            self._create_official_document()
        
        # Ghi log hoàn thành
        self.message_post(
            body=_('Biên bản bàn giao đã hoàn thành với đầy đủ chữ ký điện tử.'),
            subject=_('Hoàn thành biên bản'),
        )

    def action_open_van_ban(self):
        """Smart button: open the outgoing document linked to this handover.

        If none exists yet, create it only after the handover is signed/completed.
        """
        self.ensure_one()

        if not self.van_ban_id:
            if self.state not in ('signed', 'completed'):
                raise UserError(_('Chỉ có thể tạo văn bản chính thức sau khi biên bản đã ký.'))
            self._create_official_document()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Văn bản liên quan'),
            'res_model': 'van_ban_di',
            'res_id': self.van_ban_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_cancel(self):
        """Hủy biên bản và tự động xóa"""
        self.ensure_one()
        
        # Lưu thông tin để tạo biên bản mới
        handover_type = self.handover_type
        asset_id = self.asset_id.id
        lending_id = self.lending_id.id if self.lending_id else False
        assignment_id = self.assignment_id.id if self.assignment_id else False
        
        self.message_post(
            body=_('Biên bản %s đã bị hủy và sẽ được xóa khỏi hệ thống.') % self.name,
            subject=_('Hủy biên bản')
        )
        
        # Xóa biên bản sau khi hủy
        self.unlink()
        
        # Nếu là biên bản trả, mở form tạo biên bản trả mới
        if handover_type == 'return' and lending_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Tạo biên bản trả mới'),
                'res_model': 'dnu.asset.handover',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_handover_type': 'return',
                    'default_asset_id': asset_id,
                    'default_lending_id': lending_id,
                }
            }
        
        return {'type': 'ir.actions.act_window_close'}
    
    def _auto_assign_asset_after_return(self):
        """Tự động gán tài sản cho người nhận sau khi hoàn thành biên bản trả"""
        self.ensure_one()
        
        # Kết thúc phiếu mượn hiện tại nếu có
        if self.lending_id:
            self.lending_id.write({
                'state': 'returned',
                'date_actual_return': fields.Datetime.now()
            })
        
        # Kết thúc assignment cũ nếu có
        old_assignments = self.env['dnu.asset.assignment'].search([
            ('asset_id', '=', self.asset_id.id),
            ('date_to', '=', False),
            ('state', '=', 'active')
        ])
        if old_assignments:
            old_assignments.write({
                'date_to': fields.Date.today(),
                'state': 'returned'
            })
        
        # Tạo assignment mới cho người nhận (Kiểm kê - Bảo Trì)
        new_assignment = self.env['dnu.asset.assignment'].create({
            'asset_id': self.asset_id.id,
            'nhan_vien_id': self.nhan_vien_id.id,
            'don_vi_id': self.nhan_vien_id.don_vi_chinh_id.id if self.nhan_vien_id.don_vi_chinh_id else False,
            'date_from': fields.Date.today(),
            'state': 'active',
            'notes': _('Tự động gán sau khi hoàn thành biên bản trả %s') % self.name,
        })
        
        # Cập nhật trạng thái tài sản
        self.asset_id.write({
            'state': 'assigned',
            'assigned_nhan_vien_id': self.nhan_vien_id.id,
        })
        
        # Ghi log
        self.message_post(
            body=_('Tài sản %s đã được tự động gán cho %s (Kiểm kê - Bảo Trì) sau khi trả.') % (
                self.asset_id.name, self.nhan_vien_id.ho_va_ten
            ),
            subject=_('Tự động gán tài sản'),
        )
        
        return new_assignment
    
    def _send_signature_notification(self):
        """Gửi thông báo ký biên bản"""
        self._notify_event('pending_signature')
    
    def _create_official_document(self):
        """Tạo văn bản chính thức từ biên bản"""
        VanBanDi = self.env['van_ban_di']

        # Reuse existing document if already created earlier (e.g. before linking)
        existing = VanBanDi.search([
            ('source_model', '=', self._name),
            ('source_res_id', '=', self.id),
        ], limit=1)
        if existing:
            self.van_ban_id = existing.id
            return existing
        
        # Xác định loại biên bản
        loai_dict = {
            'assignment': 'Biên bản gán tài sản',
            'lending': 'Biên bản mượn tài sản',
            'return': 'Biên bản trả tài sản',
        }
        ten_loai = loai_dict.get(self.handover_type, 'Biên bản bàn giao')
        
        # Tạo văn bản đi với các field bắt buộc
        van_ban = VanBanDi.create({
            'so_van_ban_di': self.name,  # Số hiệu văn bản = Số biên bản
            'ten_van_ban': f'{ten_loai} - {self.asset_name}',  # Tên văn bản
            'so_hieu_van_ban': self.name,  # Số hiệu văn bản (trùng với số văn bản đi)
            'noi_nhan': self.don_vi_id.ten_don_vi if self.don_vi_id else '',
            'handler_employee_id': self.deliverer_id.id if self.deliverer_id else False,
            'signer_employee_id': self.deliverer_id.id if self.deliverer_id else False,
            'receiver_employee_ids': [(6, 0, [self.nhan_vien_id.id])] if self.nhan_vien_id else False,
            'department_id': self.don_vi_id.id if self.don_vi_id else False,
            'source_model': self._name,
            'source_res_id': self.id,
        })
        
        self.van_ban_id = van_ban.id
        return van_ban

    @api.constrains('handover_type', 'assignment_id', 'lending_id')
    def _check_unique_handover(self):
        for rec in self:
            if rec.handover_type == 'assignment' and rec.assignment_id:
                dup = self.search([
                    ('id', '!=', rec.id),
                    ('handover_type', '=', 'assignment'),
                    ('assignment_id', '=', rec.assignment_id.id),
                    ('state', '!=', 'cancelled')  # Bỏ qua biên bản đã hủy
                ], limit=1)
                if dup:
                    raise ValidationError(_('Mỗi phiếu gán chỉ được có 1 biên bản bàn giao.'))

            if rec.handover_type in ('lending', 'return') and rec.lending_id:
                dup = self.search([
                    ('id', '!=', rec.id),
                    ('handover_type', '=', rec.handover_type),
                    ('lending_id', '=', rec.lending_id.id),
                    ('state', '!=', 'cancelled')  # Bỏ qua biên bản đã hủy
                ], limit=1)
                if dup:
                    raise ValidationError(_('Mỗi phiếu mượn chỉ được có 1 biên bản cho từng loại (mượn/trả).'))
    
    def action_print_handover(self):
        """In biên bản bàn giao"""
        self.ensure_one()
        # Tạm thời thông báo chưa có report
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thông báo'),
                'message': _('Chức năng in biên bản đang được phát triển. Vui lòng sử dụng chức năng xuất sang văn bản đi.'),
                'type': 'warning',
                'sticky': False,
            }
        }
