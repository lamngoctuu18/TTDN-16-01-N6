#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import odoo
from odoo import api, SUPERUSER_ID

# Cleanup old ai.chat.wizard model
config = odoo.tools.config
config['db_name'] = 'btl_nhom6'

with api.Environment.manage():
    registry = odoo.registry('btl_nhom6')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Find and delete old model
        old_model = env['ir.model'].search([('model', '=', 'ai.chat.wizard')])
        if old_model:
            print(f"Found old model: {old_model.name}")
            # Delete related fields
            old_model.field_id.unlink()
            # Delete the model
            old_model.unlink()
            print("Old model deleted successfully")
        else:
            print("Old model not found")
        
        cr.commit()
