# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class AssetLending(models.Model):
    """Quản lý mượn/trả tài sản dùng chung"""
    _name = 'dnu.asset.lending'
    _description = 'Mượn tài sản dùng chung'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_borrow desc'

    name = fields.Char(
        string='Mã phiếu mượn',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        required=True,
        domain=[('state', '=', 'available')],
        tracking=True
    )
    borrower_id = fields.Many2one(
        'hr.employee',
        string='Người mượn (HR)',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        help='Chọn nhân viên từ hệ thống HR'
    )
    nhan_vien_muon_id = fields.Many2one(
        'nhan_vien',
        string='Người mượn',
        tracking=True,
        help='Chọn nhân viên từ hệ thống Nhân sự'
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        related='borrower_id.department_id',
        store=True
    )
    
    # Computed để hiển thị tên người mượn
    borrower_name = fields.Char(
        string='Tên người mượn',
        compute='_compute_borrower_name',
        store=True
    )
    
    @api.depends('borrower_id', 'nhan_vien_muon_id')
    def _compute_borrower_name(self):
        for rec in self:
            if rec.nhan_vien_muon_id:
                rec.borrower_name = rec.nhan_vien_muon_id.ho_va_ten
            elif rec.borrower_id:
                rec.borrower_name = rec.borrower_id.name
            else:
                rec.borrower_name = False
    
    @api.onchange('nhan_vien_muon_id')
    def _onchange_nhan_vien_muon(self):
        """Tự động điền thông tin từ nhân viên"""
        if self.nhan_vien_muon_id:
            # Tự động điền HR employee nếu có
            if self.nhan_vien_muon_id.hr_employee_id:
                self.borrower_id = self.nhan_vien_muon_id.hr_employee_id
    
    @api.onchange('borrower_id')
    def _onchange_borrower(self):
        """Tự động điền thông tin từ HR employee"""
        if self.borrower_id and self.borrower_id.nhan_vien_id:
            self.nhan_vien_muon_id = self.borrower_id.nhan_vien_id
    
    @api.depends('asset_id', 'asset_id.assignment_ids')
    def _compute_assigned_person(self):
        """Tìm người hiện được gán tài sản"""
        for rec in self:
            if rec.asset_id:
                # Tìm assignment hiện tại (chưa có date_to)
                current_assignment = self.env['dnu.asset.assignment'].search([
                    ('asset_id', '=', rec.asset_id.id),
                    ('date_to', '=', False),
                    ('state', '=', 'assigned')
                ], limit=1)
                
                if current_assignment:
                    rec.assigned_person_id = current_assignment.employee_id
                else:
                    rec.assigned_person_id = False
            else:
                rec.assigned_person_id = False
    
    # Thời gian mượn
    date_borrow = fields.Datetime(
        string='Thời gian mượn',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    date_expected_return = fields.Datetime(
        string='Dự kiến trả',
        required=True,
        tracking=True
    )
    date_actual_return = fields.Datetime(
        string='Thời gian trả thực tế',
        readonly=True,
        tracking=True
    )
    
    # Mục đích
    purpose = fields.Selection([
        ('meeting', 'Cuộc họp'),
        ('presentation', 'Thuyết trình'),
        ('training', 'Đào tạo'),
        ('event', 'Sự kiện'),
        ('other', 'Khác'),
    ], string='Mục đích', required=True, default='meeting', tracking=True)
    purpose_note = fields.Text(string='Chi tiết mục đích')
    
    # Liên kết với booking (nếu có)
    booking_id = fields.Many2one(
        'dnu.meeting.booking',
        string='Đặt phòng liên quan',
        help='Nếu mượn tài sản để sử dụng trong cuộc họp'
    )
    meeting_room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng họp',
        related='booking_id.room_id',
        store=True,
        readonly=True
    )
    location = fields.Char(
        string='Địa điểm sử dụng',
        tracking=True
    )
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('requested', 'Đã yêu cầu'),
        ('pending_approval', 'Chờ ký duyệt'),
        ('approved', 'Đã duyệt'),
        ('borrowed', 'Đang mượn'),
        ('returned', 'Đã trả'),
        ('overdue', 'Quá hạn'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
    # Phê duyệt và biên bản bàn giao
    require_approval = fields.Boolean(
        string='Yêu cầu phê duyệt',
        default=True,
        help='Yêu cầu người được gán tài sản ký duyệt trước khi cho mượn'
    )
    assigned_person_id = fields.Many2one(
        'hr.employee',
        string='Người quản lý tài sản',
        compute='_compute_assigned_person',
        store=True,
        help='Người hiện được gán quản lý tài sản này'
    )
    approval_status = fields.Selection([
        ('none', 'Chưa gửi'),
        ('pending', 'Chưa ký duyệt'),
        ('approved', 'Đã ký duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Tình trạng phê duyệt', default='none', tracking=True)
    approval_date = fields.Datetime(string='Ngày ký duyệt', readonly=True)
    approval_note = fields.Text(string='Ghi chú phê duyệt')
    is_auto_created = fields.Boolean(
        string='Tự động tạo từ đặt phòng',
        default=False,
        help='Phiếu mượn được tạo tự động từ booking'
    )
    
    # Thông tin trả
    return_condition = fields.Selection([
        ('good', 'Tốt - Như cũ'),
        ('normal', 'Bình thường'),
        ('damaged', 'Hư hỏng nhẹ'),
        ('broken', 'Hỏng nặng'),
    ], string='Tình trạng khi trả')
    return_notes = fields.Text(string='Ghi chú khi trả')
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt',
        readonly=True
    )
    returned_to = fields.Many2one(
        'res.users',
        string='Người nhận trả',
        readonly=True
    )
    
    notes = fields.Text(string='Ghi chú')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    # Nhắc nhở trả tài sản
    reminder_enabled = fields.Boolean(
        string='Bật nhắc trả',
        default=True,
        help='Gửi email nhắc nhở trước khi đến hạn trả'
    )
    reminder_days = fields.Integer(
        string='Nhắc trước (ngày)',
        default=1,
        help='Số ngày trước hạn trả để gửi nhắc nhở'
    )
    last_reminder_date = fields.Datetime(
        string='Lần nhắc gần nhất',
        readonly=True
    )
    reminder_count = fields.Integer(
        string='Số lần đã nhắc',
        default=0,
        readonly=True
    )
    
    # Biên bản bàn giao
    handover_id = fields.Many2one(
        'dnu.asset.handover',
        string='Biên bản bàn giao',
        help='Biên bản bàn giao khi mượn tài sản'
    )
    return_handover_id = fields.Many2one(
        'dnu.asset.handover',
        string='Biên bản trả',
        help='Biên bản bàn giao khi trả tài sản'
    )
    handover_state = fields.Selection(
        related='handover_id.state',
        string='Trạng thái biên bản',
        readonly=True,
        store=False
    )
    return_handover_state = fields.Selection(
        related='return_handover_id.state',
        string='Trạng thái biên bản trả',
        readonly=True,
        store=False
    )
    
    # Computed
    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        string='Quá hạn',
        store=True
    )
    duration_hours = fields.Float(
        compute='_compute_duration',
        string='Thời gian mượn (giờ)',
        store=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dnu.asset.lending') or _('New')
        return super(AssetLending, self).create(vals)

    @api.depends('date_borrow', 'date_expected_return', 'date_actual_return')
    def _compute_duration(self):
        for lending in self:
            if lending.date_borrow:
                end = lending.date_actual_return or lending.date_expected_return
                if end:
                    delta = end - lending.date_borrow
                    lending.duration_hours = delta.total_seconds() / 3600.0
                else:
                    lending.duration_hours = 0.0
            else:
                lending.duration_hours = 0.0

    @api.depends('date_expected_return', 'state')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for lending in self:
            if lending.state == 'borrowed' and lending.date_expected_return:
                lending.is_overdue = now > lending.date_expected_return
            else:
                lending.is_overdue = False

    @api.constrains('date_borrow', 'date_expected_return')
    def _check_dates(self):
        for lending in self:
            if lending.date_expected_return <= lending.date_borrow:
                raise ValidationError(_('Thời gian trả phải sau thời gian mượn!'))

    @api.constrains('asset_id', 'date_borrow', 'date_expected_return', 'state')
    def _check_asset_availability(self):
        """Kiểm tra tài sản có khả dụng trong khoảng thời gian không"""
        for lending in self:
            if lending.state in ['cancelled', 'returned']:
                continue
            
            # Tìm các phiếu mượn khác đang chồng chéo
            domain = [
                ('id', '!=', lending.id),
                ('asset_id', '=', lending.asset_id.id),
                ('state', 'in', ['approved', 'borrowed']),
                ('date_borrow', '<', lending.date_expected_return),
                ('date_expected_return', '>', lending.date_borrow),
            ]
            
            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    _('Tài sản "%s" đã được mượn trong khoảng thời gian này!\n\nXung đột với: %s') 
                    % (lending.asset_id.name, overlapping.name)
                )

    def action_request(self):
        """Gửi yêu cầu mượn và tạo biên bản nếu cần phê duyệt"""
        for lending in self:
            if lending.asset_id.state != 'available':
                raise UserError(_('Tài sản "%s" hiện không khả dụng!') % lending.asset_id.name)
            
            # Nếu yêu cầu phê duyệt, chuyển sang pending_approval và tạo biên bản
            if lending.require_approval and lending.assigned_person_id:
                lending.write({
                    'state': 'pending_approval',
                    'approval_status': 'pending'
                })
                # Tạo biên bản bàn giao và gửi thông báo
                lending._create_handover_document()
                lending._send_approval_notification()
                lending.message_post(
                    body=_('Yêu cầu mượn tài sản đã được gửi. Chờ %s ký duyệt biên bản bàn giao.') % 
                    lending.assigned_person_id.name
                )
            else:
                # Không cần phê duyệt, chuyển thẳng sang requested
                lending.write({'state': 'requested'})
                lending.message_post(body=_('Yêu cầu mượn tài sản đã được gửi'))
    
    def _create_handover_document(self):
        """Tạo biên bản bàn giao tự động"""
        self.ensure_one()
        if not self.handover_id:
            # Xác định người giao (assigned person) và người nhận (borrower)
            receiver = self.nhan_vien_muon_id or (
                self.borrower_id.nhan_vien_id if self.borrower_id else False
            )
            giver = self.assigned_person_id.nhan_vien_id if self.assigned_person_id else False
            
            if not receiver:
                raise UserError(_('Không tìm thấy thông tin người mượn trong hệ thống nhân sự!'))
            if not giver:
                raise UserError(_('Không tìm thấy thông tin người quản lý tài sản trong hệ thống nhân sự!'))
            
            handover = self.env['dnu.asset.handover'].create({
                'handover_type': 'lending',
                'lending_id': self.id,
                'asset_id': self.asset_id.id,
                'nhan_vien_giao_id': giver.id,
                'nhan_vien_nhan_id': receiver.id,
                'handover_date': self.date_borrow,
                'expected_return_date': self.date_expected_return,
                'condition_handover': 'good',
                'description': self.purpose_note or 'Biên bản bàn giao tài sản cho cuộc họp',
                'state': 'draft',
            })
            self.handover_id = handover.id
            return handover
        return self.handover_id
    
    def _send_approval_notification(self):
        """Gửi thông báo yêu cầu phê duyệt đến người quản lý tài sản"""
        self.ensure_one()
        if self.assigned_person_id and self.assigned_person_id.user_id:
            # Tạo activity cho người được gán
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.assigned_person_id.user_id.id,
                summary=_('Yêu cầu ký duyệt mượn tài sản'),
                note=_('%s yêu cầu mượn tài sản "%s" từ %s đến %s cho mục đích: %s. Vui lòng xem xét và ký duyệt.') % (
                    self.borrower_name,
                    self.asset_id.name,
                    self.date_borrow.strftime('%d/%m/%Y %H:%M'),
                    self.date_expected_return.strftime('%d/%m/%Y %H:%M'),
                    dict(self._fields['purpose'].selection).get(self.purpose)
                ),
            )
    
    def action_approve_lending(self):
        """Người quản lý tài sản ký duyệt cho mượn"""
        for lending in self:
            # Kiểm tra quyền
            current_user = self.env.user
            if lending.assigned_person_id.user_id != current_user:
                raise UserError(_('Chỉ có %s mới có quyền ký duyệt!') % lending.assigned_person_id.name)
            
            if lending.state != 'pending_approval':
                raise UserError(_('Phiếu mượn không ở trạng thái chờ phê duyệt!'))
            
            # Ký duyệt biên bản
            if lending.handover_id:
                lending.handover_id.action_submit()
                lending.handover_id.action_approve()
            
            lending.write({
                'state': 'approved',
                'approval_status': 'approved',
                'approval_date': fields.Datetime.now(),
                'approved_by': current_user.id,
            })
            lending.message_post(
                body=_('Yêu cầu mượn đã được %s ký duyệt') % current_user.name
            )
            
            # Gửi thông báo cho người mượn
            if lending.borrower_id and lending.borrower_id.user_id:
                lending.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=lending.borrower_id.user_id.id,
                    summary=_('Yêu cầu mượn tài sản đã được phê duyệt'),
                    note=_('Yêu cầu mượn tài sản "%s" của bạn đã được phê duyệt. Vui lòng liên hệ để nhận tài sản.') % 
                    lending.asset_id.name
                )
    
    def action_reject_lending(self):
        """Người quản lý tài sản từ chối cho mượn"""
        for lending in self:
            # Kiểm tra quyền
            current_user = self.env.user
            if lending.assigned_person_id.user_id != current_user:
                raise UserError(_('Chỉ có %s mới có quyền từ chối!') % lending.assigned_person_id.name)
            
            if lending.state != 'pending_approval':
                raise UserError(_('Phiếu mượn không ở trạng thái chờ phê duyệt!'))
            
            # Từ chối biên bản
            if lending.handover_id:
                lending.handover_id.write({'state': 'cancelled'})
            
            lending.write({
                'state': 'cancelled',
                'approval_status': 'rejected',
                'approval_date': fields.Datetime.now(),
            })
            lending.message_post(
                body=_('Yêu cầu mượn đã bị %s từ chối') % current_user.name
            )
            
            # Gửi thông báo cho người mượn
            if lending.borrower_id and lending.borrower_id.user_id:
                lending.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=lending.borrower_id.user_id.id,
                    summary=_('Yêu cầu mượn tài sản bị từ chối'),
                    note=_('Yêu cầu mượn tài sản "%s" của bạn đã bị từ chối. Vui lòng liên hệ với %s để biết thêm chi tiết.') % 
                    (lending.asset_id.name, lending.assigned_person_id.name)
                )


    def action_approve(self):
        """Duyệt yêu cầu mượn"""
        for lending in self:
            lending.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
            })
            lending.message_post(body=_('Yêu cầu mượn đã được duyệt bởi %s') % self.env.user.name)

    def action_reject(self):
        """Từ chối yêu cầu mượn"""
        for lending in self:
            lending.write({'state': 'cancelled'})
            lending.message_post(body=_('Yêu cầu mượn bị từ chối'))

    def action_lend(self):
        """Xác nhận giao tài sản"""
        for lending in self:
            if lending.asset_id.state not in ['available', 'assigned']:
                raise UserError(_('Tài sản không khả dụng để giao!'))

            # Bắt buộc có biên bản bàn giao đã hoàn thành
            if not lending.handover_id:
                raise UserError(_('Bắt buộc tạo Biên bản bàn giao trước khi giao tài sản.'))
            if lending.handover_id.handover_type != 'lending' or lending.handover_id.lending_id != lending:
                raise UserError(_('Biên bản bàn giao liên kết không đúng với phiếu mượn này.'))
            if lending.handover_id.state != 'completed':
                raise UserError(_('Biên bản bàn giao phải được ký và Hoàn thành trước khi giao tài sản.'))

            # Đảm bảo có biên bản bàn giao khi giao tài sản
            if not lending.handover_id:
                receiver = lending.nhan_vien_muon_id or (lending.borrower_id.nhan_vien_id if lending.borrower_id else False)
                if receiver:
                    lending.handover_id = self.env['dnu.asset.handover'].create({
                        'handover_type': 'lending',
                        'lending_id': lending.id,
                        'asset_id': lending.asset_id.id,
                        'nhan_vien_id': receiver.id,
                        'handover_date': lending.date_borrow,
                        'expected_return_date': lending.date_expected_return,
                        'condition_handover': 'good',
                    }).id
            
            lending.write({'state': 'borrowed'})
            # Cập nhật trạng thái tài sản
            lending.asset_id.write({
                'state': 'assigned',
                'assigned_to': lending.borrower_id.id,
            })
            lending.message_post(body=_('Tài sản đã được giao cho %s') % lending.borrower_id.name)

    def action_return(self):
        """Trả tài sản"""
        for lending in self:
            # Bắt buộc có biên bản trả đã hoàn thành
            if not lending.return_handover_id:
                raise UserError(_('Bắt buộc tạo Biên bản trả trước khi xác nhận trả tài sản.'))
            if lending.return_handover_id.handover_type != 'return' or lending.return_handover_id.lending_id != lending:
                raise UserError(_('Biên bản trả liên kết không đúng với phiếu mượn này.'))
            if lending.return_handover_id.state != 'completed':
                raise UserError(_('Biên bản trả phải được ký và Hoàn thành trước khi xác nhận trả tài sản.'))

            lending.write({
                'state': 'returned',
                'date_actual_return': fields.Datetime.now(),
                'returned_to': self.env.user.id,
            })
            
            # Kiểm tra xem có phiếu mượn nào khác đang active không
            other_lending = self.search([
                ('asset_id', '=', lending.asset_id.id),
                ('state', 'in', ['approved', 'borrowed']),
                ('id', '!=', lending.id),
            ], limit=1)
            
            if not other_lending:
                lending.asset_id.write({
                    'state': 'available',
                    'assigned_to': False,
                })

            # Đảm bảo có biên bản trả tài sản
            if not lending.return_handover_id:
                receiver = lending.nhan_vien_muon_id or (lending.borrower_id.nhan_vien_id if lending.borrower_id else False)
                if receiver:
                    condition_map = {
                        'good': 'good',
                        'normal': 'fair',
                        'damaged': 'poor',
                        'broken': 'damaged',
                    }
                    lending.return_handover_id = self.env['dnu.asset.handover'].create({
                        'handover_type': 'return',
                        'lending_id': lending.id,
                        'asset_id': lending.asset_id.id,
                        'nhan_vien_id': receiver.id,
                        'handover_date': fields.Datetime.now(),
                        'condition_return': condition_map.get(lending.return_condition or 'good', 'good'),
                    }).id
            
            # Tạo yêu cầu bảo trì nếu tài sản bị hỏng
            if lending.return_condition in ['damaged', 'broken']:
                maintenance_vals = {
                    'asset_id': lending.asset_id.id,
                    'maintenance_type': 'corrective',
                    'reporter_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                    'description': _('Phát hiện hư hỏng khi nhận trả từ phiếu mượn %s.\nGhi chú: %s') % 
                                   (lending.name, lending.return_notes or ''),
                    'priority': 'high' if lending.return_condition == 'broken' else 'normal',
                    'state': 'pending',
                    'lending_id': lending.id,
                    'handover_id': lending.return_handover_id.id if lending.return_handover_id else False,
                }
                self.env['dnu.asset.maintenance'].create(maintenance_vals)
            
            lending.message_post(body=_('Tài sản đã được trả lại'))

    def action_cancel(self):
        """Hủy yêu cầu mượn"""
        for lending in self:
            if lending.state == 'borrowed':
                raise UserError(_('Không thể hủy phiếu mượn đang trong trạng thái mượn!'))
            lending.write({'state': 'cancelled'})

    @api.model
    def _cron_check_overdue(self):
        """Cron job kiểm tra và cập nhật trạng thái quá hạn"""
        now = fields.Datetime.now()
        overdue_lendings = self.search([
            ('state', '=', 'borrowed'),
            ('date_expected_return', '<', now),
        ])
        
        for lending in overdue_lendings:
            lending.write({'state': 'overdue'})
            # Tạo activity nhắc nhở
            lending.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today(),
                summary=_('Tài sản quá hạn trả'),
                note=_('Phiếu mượn %s đã quá hạn. Vui lòng liên hệ người mượn.') % lending.name,
                user_id=lending.approved_by.id if lending.approved_by else self.env.user.id,
            )
            
            # Gửi email nhắc nhở
            template = self.env.ref('dnu_meeting_asset.email_template_lending_overdue', raise_if_not_found=False)
            if template:
                template.send_mail(lending.id, force_send=True)
    
    @api.model
    def _cron_send_return_reminders(self):
        """Cron job gửi nhắc nhở trả tài sản"""
        now = fields.Datetime.now()
        
        # Tìm các phiếu mượn cần nhắc
        lendings = self.search([
            ('state', '=', 'borrowed'),
            ('reminder_enabled', '=', True),
            ('date_expected_return', '!=', False),
        ])
        
        for lending in lendings:
            # Tính thời gian còn lại
            time_left = lending.date_expected_return - now
            days_left = time_left.days
            
            # Chỉ nhắc nếu còn đúng số ngày đã cài đặt
            if days_left == lending.reminder_days:
                # Kiểm tra đã nhắc hôm nay chưa
                if not lending.last_reminder_date or lending.last_reminder_date.date() < now.date():
                    lending._send_return_reminder()
                    lending.write({
                        'last_reminder_date': now,
                        'reminder_count': lending.reminder_count + 1,
                    })
    
    def _send_return_reminder(self):
        """Gửi email nhắc trả tài sản"""
        self.ensure_one()
        template = self.env.ref('dnu_meeting_asset.email_template_return_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    def action_create_handover(self):
        """Tạo biên bản bàn giao"""
        self.ensure_one()
        
        if self.handover_id:
            raise UserError(_('Biên bản bàn giao đã được tạo!'))
        
        receiver = self.nhan_vien_muon_id or (self.borrower_id.nhan_vien_id if self.borrower_id else False)
        if not receiver:
            raise UserError(_('Vui lòng chọn Người mượn (Nhân sự) để tạo biên bản.'))

        # Tạo biên bản bàn giao
        handover = self.env['dnu.asset.handover'].create({
            'handover_type': 'lending',
            'lending_id': self.id,
            'asset_id': self.asset_id.id,
            'nhan_vien_id': receiver.id,
            'handover_date': self.date_borrow,
            'expected_return_date': self.date_expected_return,
            'condition_handover': 'good',
        })
        
        self.handover_id = handover.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản bàn giao',
            'res_model': 'dnu.asset.handover',
            'res_id': handover.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_handover(self):
        """Mở biên bản bàn giao đã tạo"""
        self.ensure_one()
        if not self.handover_id:
            return self.action_create_handover()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản bàn giao',
            'res_model': 'dnu.asset.handover',
            'res_id': self.handover_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_return_handover(self):
        """Tạo biên bản trả tài sản"""
        self.ensure_one()
        
        if self.return_handover_id:
            raise UserError(_('Biên bản trả đã được tạo!'))
        
        receiver = self.nhan_vien_muon_id or (self.borrower_id.nhan_vien_id if self.borrower_id else False)
        if not receiver:
            raise UserError(_('Vui lòng chọn Người mượn (Nhân sự) để tạo biên bản.'))

        # Map tình trạng trả từ phiếu mượn -> biên bản
        condition_map = {
            'good': 'good',
            'normal': 'fair',
            'damaged': 'poor',
            'broken': 'damaged',
        }
        condition_return = condition_map.get(self.return_condition or 'good', 'good')

        # Tạo biên bản trả
        handover = self.env['dnu.asset.handover'].create({
            'handover_type': 'return',
            'lending_id': self.id,
            'asset_id': self.asset_id.id,
            'nhan_vien_id': receiver.id,
            'handover_date': fields.Datetime.now(),
            'condition_return': condition_return,
        })
        
        self.return_handover_id = handover.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản trả tài sản',
            'res_model': 'dnu.asset.handover',
            'res_id': handover.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_return_handover(self):
        """Mở biên bản trả đã tạo"""
        self.ensure_one()
        if not self.return_handover_id:
            return self.action_create_return_handover()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biên bản trả tài sản',
            'res_model': 'dnu.asset.handover',
            'res_id': self.return_handover_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def check_availability(self, asset_id, date_from, date_to, exclude_id=None):
        """Kiểm tra tài sản có khả dụng trong khoảng thời gian"""
        domain = [
            ('asset_id', '=', asset_id),
            ('state', 'in', ['approved', 'borrowed']),
            ('date_borrow', '<', date_to),
            ('date_expected_return', '>', date_from),
        ]
        
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        
        conflicts = self.search(domain)
        return (len(conflicts) == 0, conflicts)
