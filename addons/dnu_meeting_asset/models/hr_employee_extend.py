# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployeeExtend(models.Model):
    """Mở rộng hr.employee để liên kết với nhan_vien từ module nhan_su"""
    _inherit = 'hr.employee'

    # Liên kết với nhân viên từ module nhan_su
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên (Hệ thống cũ)',
        help='Liên kết với nhân viên trong module nhan_su'
    )
    
    # Thông tin bổ sung từ nhan_vien
    ma_dinh_danh = fields.Char(
        string='Mã định danh',
        related='nhan_vien_id.ma_dinh_danh',
        store=True,
        readonly=True
    )
    que_quan = fields.Char(
        string='Quê quán',
        related='nhan_vien_id.que_quan',
        readonly=True
    )
    
    # Tài sản đang được gán
    asset_ids = fields.One2many(
        'dnu.asset',
        'assigned_to',
        string='Tài sản được gán'
    )
    asset_count = fields.Integer(
        compute='_compute_asset_count',
        string='Số tài sản'
    )
    
    # Lịch sử gán tài sản
    asset_assignment_ids = fields.One2many(
        'dnu.asset.assignment',
        'employee_id',
        string='Lịch sử gán tài sản'
    )
    assignment_count = fields.Integer(
        compute='_compute_assignment_count',
        string='Số lần được gán'
    )
    
    # Lịch sử mượn tài sản
    asset_lending_ids = fields.One2many(
        'dnu.asset.lending',
        'borrower_id',
        string='Lịch sử mượn tài sản'
    )
    lending_count = fields.Integer(
        compute='_compute_lending_count',
        string='Số lần mượn'
    )
    
    # Lịch sử đặt phòng họp
    booking_ids = fields.One2many(
        'dnu.meeting.booking',
        'organizer_id',
        string='Lịch sử đặt phòng'
    )
    booking_count = fields.Integer(
        compute='_compute_booking_count',
        string='Số lần đặt phòng'
    )
    
    # Phiếu bảo trì đã báo cáo
    maintenance_reported_ids = fields.One2many(
        'dnu.asset.maintenance',
        'reporter_id',
        string='Phiếu bảo trì đã báo cáo'
    )
    
    # Phiếu bảo trì được gán (kỹ thuật viên)
    maintenance_assigned_ids = fields.One2many(
        'dnu.asset.maintenance',
        'assigned_tech_id',
        string='Phiếu bảo trì được gán'
    )
    maintenance_count = fields.Integer(
        compute='_compute_maintenance_count',
        string='Số phiếu bảo trì'
    )

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for employee in self:
            employee.asset_count = len(employee.asset_ids)

    @api.depends('asset_assignment_ids')
    def _compute_assignment_count(self):
        for employee in self:
            employee.assignment_count = len(employee.asset_assignment_ids)

    @api.depends('asset_lending_ids')
    def _compute_lending_count(self):
        for employee in self:
            employee.lending_count = len(employee.asset_lending_ids)

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for employee in self:
            employee.booking_count = len(employee.booking_ids)

    @api.depends('maintenance_reported_ids', 'maintenance_assigned_ids')
    def _compute_maintenance_count(self):
        for employee in self:
            employee.maintenance_count = len(employee.maintenance_reported_ids) + len(employee.maintenance_assigned_ids)

    def action_view_assets(self):
        """Xem tài sản được gán cho nhân viên"""
        self.ensure_one()
        return {
            'name': _('Tài sản của %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset',
            'view_mode': 'tree,form',
            'domain': [('assigned_to', '=', self.id)],
            'context': {'default_assigned_to': self.id},
        }

    def action_view_assignments(self):
        """Xem lịch sử gán tài sản"""
        self.ensure_one()
        return {
            'name': _('Lịch sử gán tài sản - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.assignment',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_lendings(self):
        """Xem lịch sử mượn tài sản"""
        self.ensure_one()
        return {
            'name': _('Lịch sử mượn tài sản - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.lending',
            'view_mode': 'tree,form',
            'domain': [('borrower_id', '=', self.id)],
            'context': {'default_borrower_id': self.id},
        }

    def action_view_bookings(self):
        """Xem lịch sử đặt phòng"""
        self.ensure_one()
        return {
            'name': _('Lịch sử đặt phòng - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.meeting.booking',
            'view_mode': 'tree,calendar,form',
            'domain': [('organizer_id', '=', self.id)],
            'context': {'default_organizer_id': self.id},
        }

    def action_view_maintenance(self):
        """Xem phiếu bảo trì liên quan"""
        self.ensure_one()
        return {
            'name': _('Phiếu bảo trì - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.maintenance',
            'view_mode': 'tree,form',
            'domain': ['|', ('reporter_id', '=', self.id), ('assigned_tech_id', '=', self.id)],
        }


    # ---------------------
    # Đồng bộ với nhan_vien
    # ---------------------
    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        # Khi tạo hr.employee mới và đã chọn nhan_vien_id, cập nhật liên kết ngược
        for emp in employees:
            if emp.nhan_vien_id and not emp.nhan_vien_id.hr_employee_id:
                emp.nhan_vien_id.hr_employee_id = emp
        return employees

    def write(self, vals):
        res = super().write(vals)
        # Nếu cập nhật nhan_vien_id thì đảm bảo liên kết 2 chiều
        if 'nhan_vien_id' in vals:
            for emp in self:
                if emp.nhan_vien_id and not emp.nhan_vien_id.hr_employee_id:
                    emp.nhan_vien_id.hr_employee_id = emp
        return res


class NhanVienExtend(models.Model):
    """Mở rộng nhan_vien để liên kết ngược với hr.employee"""
    _inherit = 'nhan_vien'

    # Liên kết với hr.employee
    hr_employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên HR',
        help='Liên kết với nhân viên trong module hr'
    )
    
    # Computed để lấy thông tin tài sản thông qua hr.employee
    asset_count = fields.Integer(
        compute='_compute_asset_info',
        string='Số tài sản'
    )
    booking_count = fields.Integer(
        compute='_compute_asset_info',
        string='Số đặt phòng'
    )

    @api.depends('hr_employee_id')
    def _compute_asset_info(self):
        for nv in self:
            if nv.hr_employee_id:
                nv.asset_count = nv.hr_employee_id.asset_count
                nv.booking_count = nv.hr_employee_id.booking_count
            else:
                nv.asset_count = 0
                nv.booking_count = 0

    # ---------------------
    # Tự động tạo hr.employee từ nhan_vien để hiển thị trong dropdown
    # ---------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_hr_employee()
        return records

    def write(self, vals):
        res = super().write(vals)
        if set(vals).intersection({'ho_va_ten', 'ho_ten_dem', 'ten', 'email', 'so_dien_thoai', 'que_quan'}):
            self._sync_hr_employee_fields()
        if 'hr_employee_id' not in vals:
            # Nếu chưa liên kết, đảm bảo tạo
            self._ensure_hr_employee()
        return res

    def _ensure_hr_employee(self):
        """Đảm bảo mỗi nhan_vien có một bản ghi hr.employee liên kết"""
        HrEmployee = self.env['hr.employee']
        for nv in self:
            if nv.hr_employee_id:
                continue
            name = nv.ho_va_ten or nv.ten or nv.ma_dinh_danh
            hr_vals = {
                'name': name,
                'nhan_vien_id': nv.id,
                'work_email': nv.email,
                'work_phone': nv.so_dien_thoai,
                'company_id': self.env.company.id,
            }
            hr_emp = HrEmployee.create(hr_vals)
            nv.hr_employee_id = hr_emp

    def _sync_hr_employee_fields(self):
        """Đồng bộ thông tin cơ bản sang hr.employee hiện có"""
        for nv in self:
            if not nv.hr_employee_id:
                continue
            name = nv.ho_va_ten or nv.ten or nv.ma_dinh_danh
            update_vals = {
                'name': name,
                'work_email': nv.email,
                'work_phone': nv.so_dien_thoai,
            }
            # Tránh ghi None nếu không có dữ liệu mới
            cleaned_vals = {k: v for k, v in update_vals.items() if v}
            if cleaned_vals:
                nv.hr_employee_id.write(cleaned_vals)

    def action_view_assets(self):
        """Xem tài sản thông qua hr.employee"""
        self.ensure_one()
        if self.hr_employee_id:
            return self.hr_employee_id.action_view_assets()
        return {'type': 'ir.actions.act_window_close'}

    def action_view_bookings(self):
        """Xem đặt phòng thông qua hr.employee"""
        self.ensure_one()
        if self.hr_employee_id:
            return self.hr_employee_id.action_view_bookings()
        return {'type': 'ir.actions.act_window_close'}
