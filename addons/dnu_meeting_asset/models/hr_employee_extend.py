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
    
    # Lấy đơn vị và chức vụ chính từ lịch sử công tác
    don_vi_chinh_id = fields.Many2one(
        'don_vi',
        compute='_compute_don_vi_chuc_vu_chinh',
        string='Đơn vị chính',
        store=True
    )
    chuc_vu_chinh_id = fields.Many2one(
        'chuc_vu',
        compute='_compute_don_vi_chuc_vu_chinh',
        string='Chức vụ chính',
        store=True
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
    ai_request_count = fields.Integer(
        compute='_compute_ai_request_count',
        string='Số lượt hỏi AI'
    )

    @api.depends('nhan_vien_id.lich_su_cong_tac_ids', 'nhan_vien_id.lich_su_cong_tac_ids.loai_chuc_vu')
    def _compute_don_vi_chuc_vu_chinh(self):
        """Lấy đơn vị và chức vụ chính từ lịch sử công tác"""
        for employee in self:
            if not employee.nhan_vien_id:
                employee.don_vi_chinh_id = False
                employee.chuc_vu_chinh_id = False
                continue
            
            # Tìm lịch sử công tác chính (loại chức vụ = 'Chính')
            lstc_chinh = employee.nhan_vien_id.lich_su_cong_tac_ids.filtered(
                lambda x: x.loai_chuc_vu == 'Chính'
            )
            
            if lstc_chinh:
                # Lấy bản ghi đầu tiên
                employee.don_vi_chinh_id = lstc_chinh[0].don_vi_id
                employee.chuc_vu_chinh_id = lstc_chinh[0].chuc_vu_id
            else:
                employee.don_vi_chinh_id = False
                employee.chuc_vu_chinh_id = False
    
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

    def _compute_ai_request_count(self):
        Request = self.env['ai.request']
        for employee in self:
            employee.ai_request_count = Request.search_count([
                ('context_model', '=', employee._name),
                ('context_res_id', '=', employee.id),
            ])

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

    def action_view_ai_history(self):
        """Xem lịch sử hỏi AI của nhân sự"""
        self.ensure_one()
        return {
            'name': _('Lịch sử hỏi AI - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ai.request',
            'view_mode': 'tree,form',
            'domain': [('context_model', '=', self._name), ('context_res_id', '=', self.id)],
            'context': {
                'default_context_model': self._name,
                'default_context_res_id': self.id,
                'default_channel': 'hr',
            },
        }

    def action_ai_hr_chat(self):
        """Mở AI Nhân sự cho nhân viên hiện tại"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '👥 AI Nhân sự',
            'res_model': 'ai.hr.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_action_type': 'chat',
                'ai_context_model': self._name,
                'ai_context_res_id': self.id,
            },
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


    def _sync_nhan_vien_from_hr(self, fields_changed=None):
        """Đồng bộ dữ liệu từ hr.employee sang nhan_vien"""
        for emp in self:
            nv = emp.nhan_vien_id
            if not nv:
                continue
            nv.with_context(sync_from_hr_employee=True)._sync_from_hr_employee(emp, fields_changed=fields_changed)


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
        if not self.env.context.get('sync_from_nhan_vien'):
            employees._sync_nhan_vien_from_hr(fields_changed={'name', 'work_email', 'work_phone', 'birthday', 'place_of_birth', 'identification_id', 'department_id', 'job_id', 'nhan_vien_id'})
        return employees

    def write(self, vals):
        res = super().write(vals)
        # Nếu cập nhật nhan_vien_id thì đảm bảo liên kết 2 chiều
        if 'nhan_vien_id' in vals:
            for emp in self:
                if emp.nhan_vien_id and not emp.nhan_vien_id.hr_employee_id:
                    emp.nhan_vien_id.hr_employee_id = emp
        if not self.env.context.get('sync_from_nhan_vien'):
            sync_fields = {'name', 'work_email', 'work_phone', 'birthday', 'place_of_birth', 'identification_id', 'department_id', 'job_id', 'nhan_vien_id'}
            if sync_fields.intersection(vals.keys()):
                self._sync_nhan_vien_from_hr(fields_changed=set(vals.keys()))
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
        if self.env.context.get('sync_from_hr_employee'):
            return res
        if set(vals).intersection({'ho_va_ten', 'ho_ten_dem', 'ten', 'email', 'so_dien_thoai', 'que_quan', 'ngay_sinh', 'ma_dinh_danh', 'lich_su_cong_tac_ids'}):
            self.with_context(sync_from_nhan_vien=True)._sync_hr_employee_fields()
        if 'hr_employee_id' not in vals:
            # Nếu chưa liên kết, đảm bảo tạo
            self._ensure_hr_employee()
        return res

    def _get_or_create_nhan_su_don_vi_from_hr(self, department):
        """Tìm hoặc tạo don_vi từ hr.department"""
        if not department:
            return False
        DonVi = self.env['don_vi']
        dv = DonVi.search([('ten_don_vi', '=', department.name)], limit=1)
        if not dv:
            dv = DonVi.create({
                'ten_don_vi': department.name,
                'ma_don_vi': getattr(department, 'code', False) or ('DV-%s' % department.id),
            })
        return dv

    def _get_or_create_nhan_su_chuc_vu_from_hr(self, job):
        """Tìm hoặc tạo chuc_vu từ hr.job"""
        if not job:
            return False
        ChucVu = self.env['chuc_vu']
        cv = ChucVu.search([('ten_chuc_vu', '=', job.name)], limit=1)
        if not cv:
            cv = ChucVu.create({
                'ten_chuc_vu': job.name,
                'ma_chuc_vu': 'CV-%s' % job.id,
            })
        return cv

    def _sync_from_hr_employee(self, hr_employee, fields_changed=None):
        """Nhận dữ liệu từ hr.employee và cập nhật nhan_vien"""
        for nv in self:
            emp = hr_employee or nv.hr_employee_id
            if not emp:
                continue
            vals = {}
            if not fields_changed or 'work_email' in fields_changed:
                if emp.work_email and emp.work_email != nv.email:
                    vals['email'] = emp.work_email
            if not fields_changed or 'work_phone' in fields_changed:
                if emp.work_phone and emp.work_phone != nv.so_dien_thoai:
                    vals['so_dien_thoai'] = emp.work_phone
            if not fields_changed or 'birthday' in fields_changed:
                if emp.birthday and emp.birthday != nv.ngay_sinh:
                    vals['ngay_sinh'] = emp.birthday
            if not fields_changed or 'place_of_birth' in fields_changed:
                if emp.place_of_birth and emp.place_of_birth != nv.que_quan:
                    vals['que_quan'] = emp.place_of_birth
            if not fields_changed or 'identification_id' in fields_changed:
                if emp.identification_id and emp.identification_id != nv.ma_dinh_danh:
                    vals['ma_dinh_danh'] = emp.identification_id
            if not fields_changed or 'name' in fields_changed:
                if emp.name and (not nv.ho_ten_dem or not nv.ten):
                    parts = emp.name.strip().split()
                    if parts:
                        vals['ten'] = parts[-1]
                        vals['ho_ten_dem'] = ' '.join(parts[:-1])

            if vals:
                nv.write(vals)

            # Đồng bộ phòng ban & chức vụ về lịch sử công tác chính
            if not fields_changed or {'department_id', 'job_id'}.intersection(fields_changed):
                don_vi = nv._get_or_create_nhan_su_don_vi_from_hr(emp.department_id)
                chuc_vu = nv._get_or_create_nhan_su_chuc_vu_from_hr(emp.job_id)
                if don_vi or chuc_vu:
                    lstc_chinh = nv.lich_su_cong_tac_ids.filtered(lambda x: x.loai_chuc_vu == 'Chính')
                    lstc_vals = {
                        'don_vi_id': don_vi.id if don_vi else False,
                        'chuc_vu_id': chuc_vu.id if chuc_vu else False,
                        'loai_chuc_vu': 'Chính',
                        'nhan_vien_id': nv.id,
                    }
                    if lstc_chinh:
                        lstc_chinh[0].write(lstc_vals)
                    else:
                        self.env['lich_su_cong_tac'].create(lstc_vals)
    
    def _get_or_create_hr_department(self, don_vi):
        """Tìm hoặc tạo hr.department từ don_vi"""
        if not don_vi:
            return False
        
        HrDepartment = self.env['hr.department']
        # Tìm department đã tồn tại (theo tên)
        dept = HrDepartment.search([('name', '=', don_vi.ten_don_vi)], limit=1)
        
        if not dept:
            # Tạo mới nếu chưa có
            dept = HrDepartment.create({
                'name': don_vi.ten_don_vi,
                'company_id': self.env.company.id,
            })
        
        return dept
    
    def _get_or_create_hr_job(self, chuc_vu, department_id=None):
        """Tìm hoặc tạo hr.job từ chuc_vu"""
        if not chuc_vu:
            return False
        
        HrJob = self.env['hr.job']
        # Tìm job đã tồn tại (theo tên và department)
        domain = [('name', '=', chuc_vu.ten_chuc_vu)]
        if department_id:
            domain.append(('department_id', '=', department_id))
        
        job = HrJob.search(domain, limit=1)
        
        if not job:
            # Tạo mới nếu chưa có
            job_vals = {
                'name': chuc_vu.ten_chuc_vu,
                'company_id': self.env.company.id,
            }
            if department_id:
                job_vals['department_id'] = department_id
            
            job = HrJob.create(job_vals)
        
        return job

    def _ensure_hr_employee(self):
        """Đảm bảo mỗi nhan_vien có một bản ghi hr.employee liên kết"""
        HrEmployee = self.env['hr.employee']
        for nv in self:
            if nv.hr_employee_id:
                continue
            name = nv.ho_va_ten or nv.ten or nv.ma_dinh_danh
            
            # Lấy đơn vị và chức vụ chính
            lstc_chinh = nv.lich_su_cong_tac_ids.filtered(
                lambda x: x.loai_chuc_vu == 'Chính'
            )
            
            hr_vals = {
                'name': name,
                'nhan_vien_id': nv.id,
                'work_email': nv.email,
                'work_phone': nv.so_dien_thoai,
                'identification_id': nv.ma_dinh_danh,
                'birthday': nv.ngay_sinh,
                'place_of_birth': nv.que_quan,
                'company_id': self.env.company.id,
            }
            
            # Ánh xạ department và job
            if lstc_chinh:
                don_vi = lstc_chinh[0].don_vi_id
                chuc_vu = lstc_chinh[0].chuc_vu_id
                
                if don_vi:
                    hr_dept = self._get_or_create_hr_department(don_vi)
                    if hr_dept:
                        hr_vals['department_id'] = hr_dept.id
                
                if chuc_vu:
                    hr_job = self._get_or_create_hr_job(chuc_vu, hr_vals.get('department_id'))
                    if hr_job:
                        hr_vals['job_id'] = hr_job.id
            
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
                'identification_id': nv.ma_dinh_danh,
                'birthday': nv.ngay_sinh,
                'place_of_birth': nv.que_quan,
            }
            
            # Đồng bộ department và job từ lịch sử công tác chính
            lstc_chinh = nv.lich_su_cong_tac_ids.filtered(
                lambda x: x.loai_chuc_vu == 'Chính'
            )
            
            if lstc_chinh:
                don_vi = lstc_chinh[0].don_vi_id
                chuc_vu = lstc_chinh[0].chuc_vu_id
                
                if don_vi:
                    hr_dept = self._get_or_create_hr_department(don_vi)
                    if hr_dept:
                        update_vals['department_id'] = hr_dept.id
                
                if chuc_vu:
                    hr_job = self._get_or_create_hr_job(chuc_vu, update_vals.get('department_id'))
                    if hr_job:
                        update_vals['job_id'] = hr_job.id
            
            # Tránh ghi None nếu không có dữ liệu mới
            cleaned_vals = {k: v for k, v in update_vals.items() if v}
            if cleaned_vals:
                nv.hr_employee_id.with_context(sync_from_nhan_vien=True).write(cleaned_vals)

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
    
    def action_sync_all_to_hr_employee(self):
        """Đồng bộ tất cả nhân viên sang hr.employee (dùng cho admin)"""
        all_nhan_vien = self.env['nhan_vien'].search([])
        synced_count = 0
        
        for nv in all_nhan_vien:
            nv._ensure_hr_employee()
            if nv.hr_employee_id:
                nv._sync_hr_employee_fields()
                synced_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đồng bộ hoàn tất'),
                'message': _('Đã đồng bộ %d nhân viên sang HR Employee') % synced_count,
                'type': 'success',
                'sticky': False,
            }
        }
