# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class AssetDashboard(models.Model):
    _name = 'dnu.asset.dashboard'
    _description = 'Dashboard Quản lý Tài sản'
    _auto = False  # Virtual model - không tạo table

    # Tổng quan tài sản
    total_assets = fields.Integer(string='Tổng số tài sản')
    total_value = fields.Float(string='Tổng giá trị (VNĐ)')
    available_assets = fields.Integer(string='Tài sản sẵn sàng')
    assigned_assets = fields.Integer(string='Tài sản đã gán')
    maintenance_assets = fields.Integer(string='Tài sản đang bảo trì')
    disposed_assets = fields.Integer(string='Tài sản đã thanh lý')
    
    # Khấu hao
    total_depreciation = fields.Float(string='Tổng khấu hao')
    current_total_value = fields.Float(string='Giá trị hiện tại')
    
    # Mượn trả
    pending_lendings = fields.Integer(string='Đơn mượn chờ duyệt')
    active_lendings = fields.Integer(string='Đơn mượn đang mượn')
    overdue_lendings = fields.Integer(string='Đơn mượn quá hạn')
    
    # Bảo trì
    scheduled_maintenance = fields.Integer(string='Bảo trì lập lịch')
    pending_maintenance = fields.Integer(string='Bảo trì chờ thực hiện')
    
    # Kiểm kê
    pending_inventories = fields.Integer(string='Kiểm kê đang thực hiện')
    
    # Thanh lý
    pending_disposals = fields.Integer(string='Thanh lý chờ duyệt')
    
    company_id = fields.Many2one('res.company', string='Công ty')

    def init(self):
        """Tạo SQL view cho dashboard"""
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW dnu_asset_dashboard AS (
                SELECT
                    1 as id,
                    COUNT(a.id) as total_assets,
                    COALESCE(SUM(a.purchase_value), 0) as total_value,
                    COUNT(CASE WHEN a.state = 'available' THEN 1 END) as available_assets,
                    COUNT(CASE WHEN a.state = 'assigned' THEN 1 END) as assigned_assets,
                    COUNT(CASE WHEN a.state = 'maintenance' THEN 1 END) as maintenance_assets,
                    COUNT(CASE WHEN a.state = 'disposed' THEN 1 END) as disposed_assets,
                    
                    COALESCE(SUM(d.total_depreciated), 0) as total_depreciation,
                    COALESCE(SUM(d.current_value), 0) as current_total_value,
                    
                    (SELECT COUNT(*) FROM dnu_asset_lending WHERE state = 'requested') as pending_lendings,
                    (SELECT COUNT(*) FROM dnu_asset_lending WHERE state = 'borrowed') as active_lendings,
                    (SELECT COUNT(*) FROM dnu_asset_lending WHERE state = 'overdue') as overdue_lendings,
                    
                    (SELECT COUNT(*) FROM dnu_asset_maintenance WHERE state = 'scheduled') as scheduled_maintenance,
                    (SELECT COUNT(*) FROM dnu_asset_maintenance WHERE state = 'pending') as pending_maintenance,
                    
                    (SELECT COUNT(*) FROM dnu_asset_inventory WHERE state IN ('in_progress', 'review')) as pending_inventories,
                    
                    (SELECT COUNT(*) FROM dnu_asset_disposal WHERE state = 'submitted') as pending_disposals,
                    
                    1 as company_id
                FROM dnu_asset a
                LEFT JOIN dnu_asset_depreciation d ON d.asset_id = a.id AND d.state = 'running'
                LIMIT 1
            )
        """)

    @api.model
    def get_dashboard_data(self):
        """Lấy dữ liệu dashboard"""
        Asset = self.env['dnu.asset']
        Lending = self.env['dnu.asset.lending']
        Maintenance = self.env['dnu.asset.maintenance']
        Inventory = self.env['dnu.asset.inventory']
        Disposal = self.env['dnu.asset.disposal']
        Depreciation = self.env['dnu.asset.depreciation']
        
        # Tài sản
        assets = Asset.search([])
        total_assets = len(assets)
        total_value = sum(assets.mapped('purchase_value'))
        available_assets = len(assets.filtered(lambda a: a.state == 'available'))
        assigned_assets = len(assets.filtered(lambda a: a.state == 'assigned'))
        maintenance_assets = len(assets.filtered(lambda a: a.state == 'maintenance'))
        disposed_assets = len(assets.filtered(lambda a: a.state == 'disposed'))
        
        # Khấu hao
        depreciations = Depreciation.search([('state', '=', 'running')])
        total_depreciation = sum(depreciations.mapped('total_depreciated'))
        current_total_value = sum(depreciations.mapped('current_value'))
        
        # Mượn trả
        pending_lendings = Lending.search_count([('state', '=', 'pending')])
        active_lendings = Lending.search_count([('state', '=', 'approved')])
        
        today = fields.Date.today()
        overdue_lendings = Lending.search_count([
            ('state', '=', 'approved'),
            ('expected_return_date', '<', today)
        ])
        
        # Bảo trì
        scheduled_maintenance = Maintenance.search_count([('state', '=', 'scheduled')])
        pending_maintenance = Maintenance.search_count([('state', '=', 'pending')])
        
        # Kiểm kê
        pending_inventories = Inventory.search_count([('state', 'in', ['in_progress', 'review'])])
        
        # Thanh lý
        pending_disposals = Disposal.search_count([('state', '=', 'submitted')])
        
        return {
            'total_assets': total_assets,
            'total_value': total_value,
            'available_assets': available_assets,
            'assigned_assets': assigned_assets,
            'maintenance_assets': maintenance_assets,
            'disposed_assets': disposed_assets,
            'total_depreciation': total_depreciation,
            'current_total_value': current_total_value,
            'pending_lendings': pending_lendings,
            'active_lendings': active_lendings,
            'overdue_lendings': overdue_lendings,
            'scheduled_maintenance': scheduled_maintenance,
            'pending_maintenance': pending_maintenance,
            'pending_inventories': pending_inventories,
            'pending_disposals': pending_disposals,
        }

    @api.model
    def get_asset_by_category(self):
        """Thống kê tài sản theo danh mục"""
        query = """
            SELECT 
                ac.name as category,
                COUNT(a.id) as count,
                SUM(a.purchase_value) as total_value
            FROM dnu_asset a
            JOIN dnu_asset_category ac ON a.category_id = ac.id
            WHERE a.state != 'disposed'
            GROUP BY ac.name
            ORDER BY count DESC
        """
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    @api.model
    def get_asset_by_state(self):
        """Thống kê tài sản theo trạng thái"""
        Asset = self.env['dnu.asset']
        
        states = dict(Asset._fields['state'].selection)
        data = []
        
        for state_key, state_label in states.items():
            count = Asset.search_count([('state', '=', state_key)])
            if count > 0:
                data.append({
                    'state': state_label,
                    'count': count,
                })
        
        return data

    @api.model
    def get_asset_by_department(self):
        """Thống kê tài sản theo phòng ban"""
        query = """
            SELECT 
                hd.name as department,
                COUNT(a.id) as count,
                SUM(a.purchase_value) as total_value
            FROM dnu_asset a
            JOIN hr_employee he ON a.assigned_to = he.id
            JOIN hr_department hd ON he.department_id = hd.id
            WHERE a.state = 'assigned'
            GROUP BY hd.name
            ORDER BY count DESC
            LIMIT 10
        """
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    @api.model
    def get_lending_trend(self, months=6):
        """Xu hướng mượn trả theo tháng"""
        start_date = fields.Date.today() - timedelta(days=months*30)
        
        query = """
            SELECT 
                TO_CHAR(lending_date, 'YYYY-MM') as month,
                COUNT(*) as total,
                SUM(CASE WHEN state = 'returned' THEN 1 ELSE 0 END) as returned,
                SUM(CASE WHEN state = 'approved' THEN 1 ELSE 0 END) as active
            FROM dnu_asset_lending
            WHERE lending_date >= %s
            GROUP BY TO_CHAR(lending_date, 'YYYY-MM')
            ORDER BY month
        """
        self.env.cr.execute(query, (start_date,))
        return self.env.cr.dictfetchall()

    @api.model
    def get_maintenance_statistics(self):
        """Thống kê bảo trì"""
        Maintenance = self.env['dnu.asset.maintenance']
        
        total = Maintenance.search_count([])
        completed = Maintenance.search_count([('state', '=', 'completed')])
        in_progress = Maintenance.search_count([('state', '=', 'in_progress')])
        scheduled = Maintenance.search_count([('state', '=', 'scheduled')])
        
        # Chi phí bảo trì
        maintenances = Maintenance.search([('state', '=', 'completed')])
        total_cost = sum(maintenances.mapped('cost'))
        
        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'scheduled': scheduled,
            'total_cost': total_cost,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
        }

    @api.model
    def get_top_valued_assets(self, limit=10):
        """Top tài sản có giá trị cao nhất"""
        query = """
            SELECT 
                a.code,
                a.name,
                ac.name as category,
                a.purchase_value,
                a.state
            FROM dnu_asset a
            JOIN dnu_asset_category ac ON a.category_id = ac.id
            WHERE a.state != 'disposed'
            ORDER BY a.purchase_value DESC
            LIMIT %s
        """
        self.env.cr.execute(query, (limit,))
        return self.env.cr.dictfetchall()

    @api.model
    def get_depreciation_overview(self):
        """Tổng quan khấu hao"""
        Depreciation = self.env['dnu.asset.depreciation']
        
        running = Depreciation.search([('state', '=', 'running')])
        
        total_original = sum(running.mapped('purchase_value'))
        total_depreciated = sum(running.mapped('total_depreciated'))
        total_current = sum(running.mapped('current_value'))
        
        depreciation_rate = (total_depreciated / total_original * 100) if total_original > 0 else 0
        
        return {
            'total_assets': len(running),
            'total_original_value': total_original,
            'total_depreciated': total_depreciated,
            'total_current_value': total_current,
            'depreciation_rate': depreciation_rate,
        }

    @api.model
    def get_upcoming_tasks(self):
        """Công việc sắp tới"""
        today = fields.Date.today()
        next_week = today + timedelta(days=7)
        
        tasks = []
        
        # Bảo trì sắp tới
        maintenances = self.env['dnu.asset.maintenance'].search([
            ('state', '=', 'scheduled'),
            ('scheduled_date', '>=', today),
            ('scheduled_date', '<=', next_week),
        ])
        
        for m in maintenances:
            tasks.append({
                'type': 'maintenance',
                'name': m.name,
                'asset': m.asset_id.name,
                'date': m.scheduled_date,
                'priority': 'high' if m.maintenance_type == 'corrective' else 'normal',
            })
        
        # Đơn mượn sắp hết hạn
        lendings = self.env['dnu.asset.lending'].search([
            ('state', '=', 'approved'),
            ('expected_return_date', '>=', today),
            ('expected_return_date', '<=', next_week),
        ])
        
        for l in lendings:
            tasks.append({
                'type': 'lending',
                'name': l.name,
                'asset': l.asset_id.name,
                'date': l.expected_return_date,
                'priority': 'normal',
            })
        
        # Sắp xếp theo ngày
        tasks.sort(key=lambda x: x['date'])
        
        return tasks[:20]  # Giới hạn 20 task

    @api.model
    def get_alerts(self):
        """Cảnh báo cần xử lý"""
        alerts = []
        
        # Đơn mượn quá hạn
        overdue_lendings = self.env['dnu.asset.lending'].search([
            ('state', '=', 'approved'),
            ('expected_return_date', '<', fields.Date.today()),
        ])
        
        if overdue_lendings:
            alerts.append({
                'type': 'danger',
                'title': _('Đơn mượn quá hạn'),
                'message': _('Có %d đơn mượn đã quá hạn trả') % len(overdue_lendings),
                'action': 'dnu_meeting_asset.action_asset_lending',
            })
        
        # Bảo trì quá hạn
        overdue_maintenance = self.env['dnu.asset.maintenance'].search([
            ('state', '=', 'scheduled'),
            ('scheduled_date', '<', fields.Date.today()),
        ])
        
        if overdue_maintenance:
            alerts.append({
                'type': 'warning',
                'title': _('Bảo trì chậm tiến độ'),
                'message': _('Có %d bảo trì đã quá ngày lập lịch') % len(overdue_maintenance),
                'action': 'dnu_meeting_asset.action_asset_maintenance',
            })
        
        # Thanh lý chờ duyệt
        pending_disposals = self.env['dnu.asset.disposal'].search([
            ('state', '=', 'submitted'),
        ])
        
        if pending_disposals:
            alerts.append({
                'type': 'info',
                'title': _('Thanh lý chờ duyệt'),
                'message': _('Có %d đề xuất thanh lý cần phê duyệt') % len(pending_disposals),
                'action': 'dnu_meeting_asset.action_asset_disposal',
            })
        
        # Kiểm kê chờ duyệt
        pending_inventories = self.env['dnu.asset.inventory'].search([
            ('state', '=', 'review'),
        ])
        
        if pending_inventories:
            alerts.append({
                'type': 'info',
                'title': _('Kiểm kê chờ duyệt'),
                'message': _('Có %d kiểm kê chờ phê duyệt kết quả') % len(pending_inventories),
                'action': 'dnu_meeting_asset.action_asset_inventory',
            })
        
        return alerts

    @api.model
    def get_asset_utilization(self):
        """Tỷ lệ sử dụng tài sản"""
        Asset = self.env['dnu.asset']
        
        total = Asset.search_count([('state', '!=', 'disposed')])
        in_use = Asset.search_count([('state', 'in', ['assigned', 'maintenance'])])
        
        utilization_rate = (in_use / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'in_use': in_use,
            'idle': total - in_use,
            'utilization_rate': utilization_rate,
        }
