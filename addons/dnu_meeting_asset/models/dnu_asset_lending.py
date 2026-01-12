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
        if self.nhan_vien_muon_id and self.nhan_vien_muon_id.hr_employee_id:
            self.borrower_id = self.nhan_vien_muon_id.hr_employee_id
    
    @api.onchange('borrower_id')
    def _onchange_borrower(self):
        """Tự động điền thông tin từ HR employee"""
        if self.borrower_id and self.borrower_id.nhan_vien_id:
            self.nhan_vien_muon_id = self.borrower_id.nhan_vien_id
    
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
    location = fields.Char(
        string='Địa điểm sử dụng',
        tracking=True
    )
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('requested', 'Đã yêu cầu'),
        ('approved', 'Đã duyệt'),
        ('borrowed', 'Đang mượn'),
        ('returned', 'Đã trả'),
        ('overdue', 'Quá hạn'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)
    
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
        """Gửi yêu cầu mượn"""
        for lending in self:
            if lending.asset_id.state != 'available':
                raise UserError(_('Tài sản "%s" hiện không khả dụng!') % lending.asset_id.name)
            lending.write({'state': 'requested'})
            lending.message_post(body=_('Yêu cầu mượn tài sản đã được gửi'))

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
            
            # Tạo yêu cầu bảo trì nếu tài sản bị hỏng
            if lending.return_condition in ['damaged', 'broken']:
                self.env['dnu.asset.maintenance'].create({
                    'asset_id': lending.asset_id.id,
                    'maintenance_type': 'corrective',
                    'reporter_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                    'description': _('Phát hiện hư hỏng khi nhận trả từ phiếu mượn %s.\nGhi chú: %s') % 
                                   (lending.name, lending.return_notes or ''),
                    'priority': 'high' if lending.return_condition == 'broken' else 'normal',
                    'state': 'pending',
                })
            
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
