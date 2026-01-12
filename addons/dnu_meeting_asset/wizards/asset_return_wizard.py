# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetReturnWizard(models.TransientModel):
    """Wizard trả tài sản mượn"""
    _name = 'dnu.asset.return.wizard'
    _description = 'Trả tài sản mượn'

    lending_id = fields.Many2one(
        'dnu.asset.lending',
        string='Phiếu mượn',
        required=True
    )
    asset_id = fields.Many2one(
        'dnu.asset',
        string='Tài sản',
        related='lending_id.asset_id',
        readonly=True
    )
    borrower_id = fields.Many2one(
        'hr.employee',
        string='Người mượn',
        related='lending_id.borrower_id',
        readonly=True
    )
    
    return_condition = fields.Selection([
        ('good', 'Tốt - Như cũ'),
        ('normal', 'Bình thường'),
        ('damaged', 'Hư hỏng nhẹ'),
        ('broken', 'Hỏng nặng'),
    ], string='Tình trạng khi trả', required=True, default='good')
    
    return_notes = fields.Text(string='Ghi chú')
    create_maintenance = fields.Boolean(
        string='Tạo yêu cầu bảo trì',
        compute='_compute_create_maintenance',
        store=True,
        readonly=False
    )
    maintenance_description = fields.Text(string='Mô tả hư hỏng')

    @api.depends('return_condition')
    def _compute_create_maintenance(self):
        for wizard in self:
            wizard.create_maintenance = wizard.return_condition in ['damaged', 'broken']

    def action_return(self):
        """Xác nhận trả tài sản"""
        self.ensure_one()
        
        self.lending_id.write({
            'return_condition': self.return_condition,
            'return_notes': self.return_notes,
        })
        
        self.lending_id.action_return()
        
        # Tạo yêu cầu bảo trì nếu cần
        if self.create_maintenance and self.maintenance_description:
            self.env['dnu.asset.maintenance'].create({
                'asset_id': self.asset_id.id,
                'maintenance_type': 'corrective',
                'reporter_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'description': self.maintenance_description,
                'priority': 'high' if self.return_condition == 'broken' else 'normal',
                'state': 'pending',
            })
        
        return {'type': 'ir.actions.act_window_close'}
