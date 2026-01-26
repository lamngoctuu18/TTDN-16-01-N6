from odoo import models, fields, api

from odoo.exceptions import UserError

class VanBanDen(models.Model):
    _name = 'van_ban_den'
    _description = 'Bảng chứa thông tin văn bản đến'
    _rec_name = 'ten_van_ban'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    so_van_ban_den = fields.Char("Số văn bản đến", required=True)
    ten_van_ban = fields.Char("Tên văn bản", required=True, tracking=True)
    so_hieu_van_ban = fields.Char("Số hiệu văn bản", required=True)
    noi_gui_den = fields.Char("Nơi gửi đến")
    
    # Loại yêu cầu duyệt
    request_type = fields.Selection([
        ('normal', 'Văn bản thường'),
        ('booking_approval', 'Duyệt đặt phòng họp'),
        ('lending_approval', 'Duyệt mượn thiết bị'),
        ('maintenance_approval', 'Duyệt bảo trì'),
        ('disposal_approval', 'Duyệt thanh lý'),
        ('meeting_minutes_approval', 'Ký biên bản cuộc họp'),
    ], string='Loại yêu cầu', default='normal', tracking=True)
    
    # Trạng thái duyệt
    approval_state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái duyệt', default='draft', tracking=True)
    
    approver_id = fields.Many2one('nhan_vien', string='Người duyệt', tracking=True)
    approval_date = fields.Datetime(string='Ngày duyệt', readonly=True)
    approval_note = fields.Text(string='Ghi chú duyệt')
    requester_id = fields.Many2one('nhan_vien', string='Người yêu cầu')
    
    # Biên bản cuộc họp (chỉ dùng cho meeting_minutes_approval)
    meeting_minutes = fields.Html(string='Nội dung biên bản', help='Nội dung biên bản cuộc họp do AI tạo ra, có thể chỉnh sửa trước khi ký')
    meeting_subject = fields.Char(string='Chủ đề cuộc họp')
    meeting_date = fields.Datetime(string='Thời gian họp')
    
    # Chữ ký điện tử
    signature = fields.Binary(string='Chữ ký người duyệt')
    signature_date = fields.Datetime(string='Ngày ký', readonly=True)
    is_signed = fields.Boolean(string='Đã ký', compute='_compute_is_signed', store=True)
    
    # Liên kết văn bản đi phản hồi
    van_ban_di_id = fields.Many2one('van_ban_di', string='Văn bản đi phản hồi', readonly=True)

    handler_employee_id = fields.Many2one('nhan_vien', string="Cán bộ xử lý")
    signer_employee_id = fields.Many2one('nhan_vien', string="Người ký")
    receiver_employee_ids = fields.Many2many('nhan_vien', 'van_ban_den_receiver_rel', 'van_ban_id', 'employee_id', string="Người nhận / phối hợp")
    department_id = fields.Many2one('don_vi', string="Phòng/Ban", compute='_compute_department', store=True)
    due_date = fields.Date(string="Hạn xử lý")

    # Link back to business document (e.g., bảo trì/thanh lý/luân chuyển/phòng họp)
    source_model = fields.Char(string='Nguồn (Model)', index=True)
    source_res_id = fields.Integer(string='Nguồn (ID)', index=True)
    is_asset_document = fields.Boolean(
        string='Liên quan tài sản/phòng họp',
        compute='_compute_is_asset_document',
        store=True,
        index=True,
        readonly=True,
        help='Đánh dấu văn bản đến được liên kết từ nghiệp vụ tài sản/phòng họp'
    )

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

    @api.depends('signature')
    def _compute_is_signed(self):
        for record in self:
            record.is_signed = bool(record.signature)
    
    @api.depends('approver_id', 'handler_employee_id', 'signer_employee_id')
    def _compute_department(self):
        for record in self:
            # Ưu tiên lấy phòng ban từ người duyệt, người ký, rồi đến cán bộ xử lý
            if record.approver_id and record.approver_id.don_vi_chinh_id:
                record.department_id = record.approver_id.don_vi_chinh_id
            elif record.signer_employee_id and record.signer_employee_id.don_vi_chinh_id:
                record.department_id = record.signer_employee_id.don_vi_chinh_id
            elif record.handler_employee_id and record.handler_employee_id.don_vi_chinh_id:
                record.department_id = record.handler_employee_id.don_vi_chinh_id
            else:
                record.department_id = False

    @api.depends('source_model')
    def _compute_is_asset_document(self):
        for rec in self:
            rec.is_asset_document = bool(rec.source_model and rec.source_model.startswith('dnu.'))

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

    def action_open_source(self):
        self.ensure_one()
        if not self.source_model or not self.source_res_id:
            raise UserError('Văn bản này chưa được liên kết với nghiệp vụ nào.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nghiệp vụ liên quan',
            'res_model': self.source_model,
            'res_id': self.source_res_id,
            'view_mode': 'form',
            'target': 'current',
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

    # =====================
    # APPROVAL WORKFLOW
    # =====================
    
    def action_submit_approval(self):
        """Gửi yêu cầu duyệt"""
        for rec in self:
            if rec.approval_state != 'draft':
                continue
            rec.write({'approval_state': 'pending'})
            # Tạo activity cho người duyệt
            if rec.approver_id and rec.approver_id.hr_employee_id and rec.approver_id.hr_employee_id.user_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=rec.approver_id.hr_employee_id.user_id.id,
                    summary='Yêu cầu duyệt: %s' % rec.ten_van_ban,
                    note='Có yêu cầu duyệt văn bản đến. Vui lòng xem xét và phê duyệt.',
                )
            rec.message_post(body='Yêu cầu duyệt đã được gửi đến %s' % (rec.approver_id.ho_va_ten or 'Ban Giám đốc'))
    
    def action_sign(self):
        """Mở wizard để ký văn bản"""
        self.ensure_one()
        return {
            'name': 'Ký văn bản',
            'type': 'ir.actions.act_window',
            'res_model': 'van_ban_den.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_van_ban_id': self.id},
        }
    
    def action_approve(self):
        """Phê duyệt yêu cầu - yêu cầu đã ký trước (hoặc bypass từ wizard)"""
        for rec in self:
            if rec.approval_state != 'pending':
                continue
            # Kiểm tra chữ ký (bypass nếu gọi từ wizard đã ký)
            if not rec.is_signed and not self.env.context.get('from_sign_wizard'):
                raise UserError('Vui lòng ký văn bản trước khi duyệt!')
            
            rec.write({
                'approval_state': 'approved',
                'approval_date': fields.Datetime.now(),
                'signer_employee_id': rec.approver_id.id if rec.approver_id else False,
            })
            
            # Tạo văn bản đi phản hồi
            van_ban_di = rec._create_van_ban_di_response()
            
            # Cập nhật nghiệp vụ nguồn
            rec._update_source_on_approval(approved=True)
            
            # Thông báo cho người yêu cầu
            rec._notify_requester(approved=True)
            
            rec.activity_feedback(['mail.mail_activity_data_todo'])
            rec.message_post(body='Yêu cầu đã được PHÊ DUYỆT và KÝ bởi %s. Văn bản đi: %s' % (
                self.env.user.name, 
                van_ban_di.so_van_ban_di if van_ban_di else '-'
            ))
    
    def action_approve_and_sign(self):
        """Duyệt và ký cùng lúc - mở wizard"""
        self.ensure_one()
        if self.approval_state != 'pending':
            raise UserError('Văn bản không ở trạng thái chờ duyệt!')
        return {
            'name': 'Duyệt và Ký văn bản',
            'type': 'ir.actions.act_window',
            'res_model': 'van_ban_den.sign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_van_ban_id': self.id,
                'approve_after_sign': True,
            },
        }
    
    def action_reject(self):
        """Từ chối yêu cầu"""
        for rec in self:
            if rec.approval_state != 'pending':
                continue
            rec.write({
                'approval_state': 'rejected',
                'approval_date': fields.Datetime.now(),
            })
            # Cập nhật nghiệp vụ nguồn
            rec._update_source_on_approval(approved=False)
            # Thông báo cho người yêu cầu
            rec._notify_requester(approved=False)
            rec.activity_feedback(['mail.mail_activity_data_todo'])
            rec.message_post(body='Yêu cầu đã bị TỪ CHỐI bởi %s. Ghi chú: %s' % (self.env.user.name, rec.approval_note or '-'))
    
    def _create_van_ban_di_response(self):
        """Tạo văn bản đi phản hồi sau khi duyệt"""
        self.ensure_one()
        if self.van_ban_di_id:
            return self.van_ban_di_id
        
        # Xác định tên văn bản đi dựa trên loại yêu cầu
        type_labels = {
            'booking_approval': 'Phê duyệt đặt phòng họp',
            'lending_approval': 'Phê duyệt mượn thiết bị',
            'maintenance_approval': 'Phê duyệt bảo trì',
            'disposal_approval': 'Phê duyệt thanh lý',
            'meeting_minutes_approval': 'Biên bản cuộc họp',
        }
        type_label = type_labels.get(self.request_type, 'Phản hồi văn bản')
        
        # Lấy số văn bản đi tự động
        so_van_ban = self.env['ir.sequence'].next_by_code('van_ban_di.approval_response') or ('PD-%s' % self.id)
        
        # Xác định nơi nhận (người yêu cầu / phòng ban)
        noi_nhan = ''
        receiver_ids = []
        if self.requester_id:
            noi_nhan = self.requester_id.ho_va_ten or ''
            if self.requester_id.don_vi_chinh_id:
                noi_nhan += ' - ' + self.requester_id.don_vi_chinh_id.ten_don_vi
            receiver_ids.append(self.requester_id.id)
        
        # Nếu là biên bản cuộc họp, thêm người tham dự vào danh sách nhận
        if self.request_type == 'meeting_minutes_approval' and self.source_model and self.source_res_id:
            SourceModel = self.env.get(self.source_model)
            if SourceModel:
                source_record = SourceModel.browse(self.source_res_id).exists()
                if source_record and hasattr(source_record, 'attendee_ids'):
                    for attendee in source_record.attendee_ids:
                        if attendee.nhan_vien_id and attendee.nhan_vien_id.id not in receiver_ids:
                            receiver_ids.append(attendee.nhan_vien_id.id)
        
        # Tạo nội dung văn bản đi
        source_name = ''
        if self.source_model and self.source_res_id:
            SourceModel = self.env.get(self.source_model)
            if SourceModel:
                source_record = SourceModel.browse(self.source_res_id).exists()
                if source_record:
                    source_name = getattr(source_record, 'name', '') or getattr(source_record, 'subject', '') or str(source_record.id)
        
        # Nội dung văn bản đi
        van_ban_content = self.meeting_minutes if self.request_type == 'meeting_minutes_approval' and self.meeting_minutes else ''
        
        van_ban_di = self.env['van_ban_di'].create({
            'so_van_ban_di': so_van_ban,
            'ten_van_ban': '%s - %s' % (type_label, self.meeting_subject or source_name or self.ten_van_ban),
            'so_hieu_van_ban': so_van_ban,
            'noi_nhan': noi_nhan,
            'signer_employee_id': self.approver_id.id if self.approver_id else False,
            'handler_employee_id': self.approver_id.id if self.approver_id else False,
            'department_id': self.approver_id.don_vi_chinh_id.id if self.approver_id and self.approver_id.don_vi_chinh_id else False,
            'receiver_employee_ids': [(6, 0, receiver_ids)] if receiver_ids else False,
            'source_model': self.source_model,
            'source_res_id': self.source_res_id,
            'noi_dung': van_ban_content,  # Lưu nội dung biên bản vào văn bản đi
        })
        
        self.van_ban_di_id = van_ban_di
        return van_ban_di
    
    def _notify_requester(self, approved=True):
        """Gửi thông báo cho người yêu cầu sau khi duyệt/từ chối"""
        self.ensure_one()
        if not self.requester_id or not self.requester_id.hr_employee_id:
            return
        
        user = self.requester_id.hr_employee_id.user_id
        if not user:
            return
        
        if approved:
            summary = '✅ Yêu cầu đã được duyệt: %s' % self.ten_van_ban
            note = 'Yêu cầu của bạn đã được PHÊ DUYỆT bởi %s.\n' % (self.approver_id.ho_va_ten if self.approver_id else 'Ban Giám đốc')
            if self.van_ban_di_id:
                note += 'Văn bản phản hồi: %s' % self.van_ban_di_id.so_van_ban_di
        else:
            summary = '❌ Yêu cầu bị từ chối: %s' % self.ten_van_ban
            note = 'Yêu cầu của bạn đã bị TỪ CHỐI.\nLý do: %s' % (self.approval_note or 'Không có ghi chú')
        
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=user.id,
            summary=summary,
            note=note,
        )
    
    def _update_source_on_approval(self, approved=True):
        """Cập nhật trạng thái nghiệp vụ nguồn khi duyệt/từ chối"""
        self.ensure_one()
        if not self.source_model or not self.source_res_id:
            self.message_post(body='⚠️ Không tìm thấy nghiệp vụ nguồn để cập nhật (source_model=%s, source_res_id=%s)' % (self.source_model, self.source_res_id))
            return
        
        SourceModel = self.env.get(self.source_model)
        if not SourceModel:
            self.message_post(body='⚠️ Không tìm thấy model nguồn: %s' % self.source_model)
            return
        
        source_record = SourceModel.browse(self.source_res_id).exists()
        if not source_record:
            self.message_post(body='⚠️ Bản ghi nguồn không tồn tại: %s#%s' % (self.source_model, self.source_res_id))
            return
        
        if self.request_type == 'booking_approval':
            if approved:
                # Xác nhận đặt phòng trực tiếp bằng cách update state
                current_state = source_record.state if hasattr(source_record, 'state') else 'unknown'
                if current_state == 'submitted':
                    try:
                        # Cập nhật trực tiếp state thay vì gọi action_confirm để tránh vòng lặp check
                        source_record.write({'state': 'confirmed'})
                        
                        # Tạo calendar event
                        if hasattr(source_record, '_create_calendar_event'):
                            source_record._create_calendar_event()
                        
                        # Tạo phiếu mượn tài sản tự động cho các thiết bị được chọn
                        if hasattr(source_record, 'required_equipment_ids') and source_record.required_equipment_ids:
                            if hasattr(source_record, '_create_auto_lending_records'):
                                source_record._create_auto_lending_records()
                        
                        # Gửi email xác nhận
                        if hasattr(source_record, '_send_confirmation_email'):
                            source_record._send_confirmation_email()
                        
                        # Gửi email thông báo cho tất cả người tham dự
                        if hasattr(source_record, '_send_notification_emails'):
                            source_record._send_notification_emails()
                        
                        source_record.message_post(body='Đặt phòng đã được xác nhận từ văn bản duyệt: %s' % self.ten_van_ban)
                        self.message_post(body='✅ Đã xác nhận đặt phòng: %s' % source_record.name)
                    except Exception as e:
                        self.message_post(body='❌ Lỗi khi xác nhận đặt phòng: %s' % str(e))
                elif current_state == 'confirmed':
                    self.message_post(body='ℹ️ Đặt phòng đã được xác nhận trước đó: %s' % source_record.name)
                else:
                    self.message_post(body='⚠️ Trạng thái booking không phải "submitted" (hiện tại: %s)' % current_state)
            else:
                # Từ chối booking
                if hasattr(source_record, 'action_cancel'):
                    source_record.write({'cancellation_reason': self.approval_note or 'Bị từ chối bởi Ban Giám đốc'})
                    source_record.action_cancel()
                    self.message_post(body='❌ Đã từ chối đặt phòng: %s' % source_record.name)
        
        elif self.request_type == 'lending_approval':
            if approved:
                # Duyệt mượn thiết bị trực tiếp
                current_state = source_record.state if hasattr(source_record, 'state') else 'unknown'
                if current_state in ['requested', 'pending_approval']:
                    try:
                        source_record.write({'state': 'approved'})
                        source_record.message_post(body='Mượn thiết bị đã được duyệt từ văn bản: %s' % self.ten_van_ban)
                        self.message_post(body='✅ Đã duyệt mượn thiết bị: %s' % source_record.name)
                    except Exception as e:
                        self.message_post(body='❌ Lỗi khi duyệt mượn thiết bị: %s' % str(e))
                elif current_state == 'approved':
                    self.message_post(body='ℹ️ Mượn thiết bị đã được duyệt trước đó: %s' % source_record.name)
                else:
                    self.message_post(body='⚠️ Trạng thái lending không hợp lệ (hiện tại: %s)' % current_state)
            else:
                # Từ chối mượn
                if hasattr(source_record, 'action_cancel'):
                    source_record.write({'notes': self.approval_note or 'Bị từ chối bởi Ban Giám đốc'})
                    source_record.action_cancel()
                    self.message_post(body='❌ Đã từ chối mượn thiết bị: %s' % source_record.name)
    
    def action_sync_source_status(self):
        """Đồng bộ lại trạng thái nghiệp vụ nguồn từ văn bản đã duyệt"""
        for rec in self:
            if rec.approval_state == 'approved' and rec.source_model and rec.source_res_id:
                rec._update_source_on_approval(approved=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đồng bộ thành công',
                'message': 'Đã đồng bộ trạng thái nghiệp vụ nguồn',
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def get_director_approvers(self):
        """Lấy danh sách người duyệt từ phòng Giám đốc (Giám đốc, Phó Giám đốc)"""
        # Tìm đơn vị Giám đốc / Ban Giám đốc
        DonVi = self.env['don_vi']
        director_units = DonVi.search([
            '|', '|', '|',
            ('ten_don_vi', 'ilike', 'Giám đốc'),
            ('ten_don_vi', 'ilike', 'Ban Giám đốc'),
            ('ten_don_vi', 'ilike', 'Administration'),
            ('ma_don_vi', 'ilike', 'BGD'),
        ])
        
        if not director_units:
            return self.env['nhan_vien']
        
        # Tìm nhân viên thuộc phòng Giám đốc với chức vụ phù hợp
        NhanVien = self.env['nhan_vien']
        LichSuCongTac = self.env['lich_su_cong_tac']
        
        lstc_records = LichSuCongTac.search([
            ('don_vi_id', 'in', director_units.ids),
            ('loai_chuc_vu', '=', 'Chính'),
        ])
        
        approvers = lstc_records.mapped('nhan_vien_id')
        return approvers
    
    @api.model
    def create_approval_request(self, source_record, request_type, requester=None, approver=None, due_date=None, note=None):
        """Tạo văn bản đến yêu cầu duyệt từ nghiệp vụ"""
        # Xác định người yêu cầu
        if not requester:
            if hasattr(source_record, 'nhan_vien_to_chuc_id') and source_record.nhan_vien_to_chuc_id:
                requester = source_record.nhan_vien_to_chuc_id
            elif hasattr(source_record, 'nhan_vien_muon_id') and source_record.nhan_vien_muon_id:
                requester = source_record.nhan_vien_muon_id
            elif hasattr(source_record, 'organizer_id') and source_record.organizer_id:
                requester = source_record.organizer_id.nhan_vien_id if hasattr(source_record.organizer_id, 'nhan_vien_id') else None
            elif hasattr(source_record, 'borrower_id') and source_record.borrower_id:
                requester = source_record.borrower_id.nhan_vien_id if hasattr(source_record.borrower_id, 'nhan_vien_id') else None
        
        # Xác định người duyệt (mặc định là Ban Giám đốc)
        if not approver:
            directors = self.get_director_approvers()
            approver = directors[0] if directors else None
        
        # Xác định hạn xử lý
        if not due_date:
            if hasattr(source_record, 'start_datetime') and source_record.start_datetime:
                due_date = source_record.start_datetime.date()
            elif hasattr(source_record, 'date_borrow') and source_record.date_borrow:
                due_date = source_record.date_borrow.date()
            else:
                due_date = fields.Date.today()
        
        # Tạo tên và số văn bản
        type_labels = {
            'booking_approval': 'Yêu cầu duyệt đặt phòng',
            'lending_approval': 'Yêu cầu duyệt mượn thiết bị',
            'maintenance_approval': 'Yêu cầu duyệt bảo trì',
            'disposal_approval': 'Yêu cầu duyệt thanh lý',
        }
        type_label = type_labels.get(request_type, 'Yêu cầu duyệt')
        
        source_name = getattr(source_record, 'name', '') or getattr(source_record, 'subject', '') or str(source_record.id)
        ten_van_ban = '%s - %s' % (type_label, source_name)
        
        # Tạo số văn bản tự động
        so_van_ban = self.env['ir.sequence'].next_by_code('van_ban_den.approval') or ('YC-%s' % source_record.id)
        
        vals = {
            'so_van_ban_den': so_van_ban,
            'ten_van_ban': ten_van_ban,
            'so_hieu_van_ban': so_van_ban,
            'request_type': request_type,
            'approval_state': 'pending',
            'source_model': source_record._name,
            'source_res_id': source_record.id,
            'requester_id': requester.id if requester else False,
            'approver_id': approver.id if approver else False,
            'handler_employee_id': approver.id if approver else False,
            'noi_gui_den': requester.don_vi_chinh_id.ten_don_vi if requester and requester.don_vi_chinh_id else 'Nội bộ',
            'due_date': due_date,
        }
        
        van_ban = self.create(vals)
        
        # Tạo activity cho người duyệt
        if approver and approver.hr_employee_id and approver.hr_employee_id.user_id:
            van_ban.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=approver.hr_employee_id.user_id.id,
                summary='Cần duyệt: %s' % ten_van_ban,
                note=note or 'Có yêu cầu duyệt mới. Vui lòng xem xét và phê duyệt.',
            )
        
        van_ban.message_post(body='Yêu cầu duyệt được tạo tự động từ %s' % source_name)
        
        return van_ban
    
    @api.model
    def create_meeting_minutes_request(self, booking, minutes_html):
        """
        Tạo văn bản đến cho biên bản cuộc họp cần ký
        Args:
            booking: bản ghi dnu.meeting.booking
            minutes_html: nội dung biên bản HTML
        """
        if not booking or not minutes_html:
            raise UserError(_('Thiếu thông tin cuộc họp hoặc nội dung biên bản!'))
        
        # Tìm người duyệt (Ban Giám đốc)
        directors = self.get_director_approvers()
        if not directors:
            raise UserError(_('Không tìm thấy người thuộc Ban Giám đốc để ký biên bản!'))
        
        director = directors[0]  # Lấy người đầu tiên
        
        # Tạo tên văn bản
        meeting_subject = booking.subject or 'cuộc họp'
        ten_van_ban = 'Biên bản cuộc họp - %s' % meeting_subject
        
        # Tạo số văn bản tự động  
        so_van_ban = self.env['ir.sequence'].next_by_code('van_ban_den.approval') or 'BB/%s' % booking.id
        
        vals = {
            'so_van_ban_den': so_van_ban,
            'ten_van_ban': ten_van_ban,
            'so_hieu_van_ban': so_van_ban,
            'request_type': 'meeting_minutes_approval',
            'approval_state': 'pending',
            'source_model': 'dnu.meeting.booking',
            'source_res_id': booking.id,
            'requester_id': booking.nhan_vien_to_chuc_id.id if booking.nhan_vien_to_chuc_id else False,
            'approver_id': director.id,
            'handler_employee_id': director.id,
            'noi_gui_den': booking.nhan_vien_to_chuc_id.don_vi_chinh_id.ten_don_vi if booking.nhan_vien_to_chuc_id and booking.nhan_vien_to_chuc_id.don_vi_chinh_id else 'Nội bộ',
            'due_date': booking.start_datetime.date() if booking.start_datetime else fields.Date.today(),
            'meeting_minutes': minutes_html,
            'meeting_subject': booking.subject,
            'meeting_date': booking.start_datetime,
        }
        
        van_ban = self.create(vals)
        
        # Tạo activity cho người ký
        if director.hr_employee_id and director.hr_employee_id.user_id:
            van_ban.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=director.hr_employee_id.user_id.id,
                summary='Cần ký biên bản cuộc họp: %s' % meeting_subject,
                note='Có biên bản cuộc họp cần ký. Vui lòng xem xét và ký duyệt.',
            )
        
        van_ban.message_post(body='Biên bản cuộc họp được tạo từ AI Meeting Assistant')
        
        return van_ban
