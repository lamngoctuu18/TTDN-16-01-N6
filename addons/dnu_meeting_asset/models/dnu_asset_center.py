# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DnuAssetCenter(models.TransientModel):
    _name = 'dnu.asset.center'
    _description = 'Trung tâm quản lý tài sản'

    # KPI Fields
    total_assets = fields.Integer(string='Tổng tài sản', compute='_compute_kpis')
    assigned_count = fields.Integer(string='Đang gán', compute='_compute_kpis')
    borrowed_count = fields.Integer(string='Đang mượn', compute='_compute_kpis')
    overdue_count = fields.Integer(string='Quá hạn', compute='_compute_kpis')
    maintenance_count = fields.Integer(string='Đang bảo trì', compute='_compute_kpis')
    pending_signature_count = fields.Integer(string='Chờ ký', compute='_compute_kpis')
    upcoming_maintenance_count = fields.Integer(string='Bảo trì sắp tới', compute='_compute_kpis')
    available_count = fields.Integer(string='Sẵn sàng', compute='_compute_kpis')

    @api.depends()
    def _compute_kpis(self):
        for record in self:
            # Tổng tài sản
            record.total_assets = self.env['dnu.asset'].search_count([])
            
            # Tài sản đang gán
            record.assigned_count = self.env['dnu.asset'].search_count([
                ('state', '=', 'assigned')
            ])
            
            # Tài sản đang mượn
            record.borrowed_count = self.env['dnu.asset'].search_count([
                ('state', '=', 'on_loan')
            ])
            
            # Tài sản sẵn sàng
            record.available_count = self.env['dnu.asset'].search_count([
                ('state', '=', 'available')
            ])
            
            # Phiếu mượn quá hạn
            record.overdue_count = self.env['dnu.asset.lending'].search_count([
                ('state', '=', 'overdue')
            ])
            
            # Tài sản đang bảo trì
            record.maintenance_count = self.env['dnu.asset.maintenance'].search_count([
                ('state', '=', 'in_progress')
            ])
            
            # Biên bản chờ ký
            record.pending_signature_count = self.env['dnu.asset.handover'].search_count([
                ('state', 'in', ['draft', 'pending_signature'])
            ])
            
            # Bảo trì định kỳ sắp tới (trong 7 ngày)
            today = fields.Date.today()
            next_week = fields.Date.add(today, days=7)
            record.upcoming_maintenance_count = self.env['dnu.asset.maintenance.schedule'].search_count([
                ('next_maintenance_date', '>=', today),
                ('next_maintenance_date', '<=', next_week),
                ('active', '=', True)
            ])

    def action_open_assets(self):
        """Mở danh sách tài sản"""
        return {
            'name': 'Tài sản',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset',
            'view_mode': 'kanban,tree,form,pivot,graph',
            'target': 'current',
        }

    def action_open_categories(self):
        """Mở danh mục tài sản"""
        return {
            'name': 'Danh mục',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.category',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_assignments(self):
        """Mở lịch sử gán"""
        return {
            'name': 'Lịch sử gán',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.assignment',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_open_lendings(self):
        """Mở danh sách mượn"""
        return {
            'name': 'Mượn tài sản',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.lending',
            'view_mode': 'kanban,tree,form',
            'target': 'current',
        }

    def action_open_maintenance(self):
        """Mở bảo trì"""
        return {
            'name': 'Bảo trì',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.maintenance',
            'view_mode': 'kanban,tree,calendar,form',
            'target': 'current',
        }

    def action_open_handovers(self):
        """Mở biên bản bàn giao"""
        return {
            'name': 'Biên bản bàn giao',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.handover',
            'view_mode': 'kanban,tree,form',
            'target': 'current',
        }

    def action_open_schedules(self):
        """Mở lịch bảo trì định kỳ"""
        return {
            'name': 'Lịch bảo trì định kỳ',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.maintenance.schedule',
            'view_mode': 'calendar,tree,form',
            'target': 'current',
        }

    def action_create_asset(self):
        """Tạo tài sản mới"""
        return {
            'name': 'Tạo tài sản',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_lending(self):
        """Tạo phiếu mượn mới"""
        return {
            'name': 'Tạo phiếu mượn',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.lending',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_handover(self):
        """Tạo biên bản mới"""
        return {
            'name': 'Tạo biên bản',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.handover',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_maintenance(self):
        """Tạo bảo trì mới"""
        return {
            'name': 'Tạo bảo trì',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.maintenance',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_schedule(self):
        """Lập lịch bảo trì định kỳ"""
        return {
            'name': 'Lập lịch định kỳ',
            'type': 'ir.actions.act_window',
            'res_model': 'dnu.asset.maintenance.schedule',
            'view_mode': 'form',
            'target': 'new',
        }
