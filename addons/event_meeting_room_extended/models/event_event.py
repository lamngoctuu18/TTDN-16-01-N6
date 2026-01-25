# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class EventEvent(models.Model):
    _inherit = 'event.event'

    # Community settings (inherited from type)
    allow_community = fields.Boolean(
        string='Bật Cộng Đồng',
        compute='_compute_community_settings',
        store=True,
        readonly=False,
        help='Cho phép trang cộng đồng với phòng họp'
    )
    allow_room_creation = fields.Boolean(
        string='Cho Phép Tạo Phòng',
        compute='_compute_community_settings',
        store=True,
        readonly=False,
    )
    
    # Meeting rooms
    meeting_room_ids = fields.One2many(
        'event.meeting.room',
        'event_id',
        string='Phòng Họp'
    )
    meeting_room_count = fields.Integer(
        string='Số Phòng',
        compute='_compute_meeting_room_count',
        store=True
    )
    active_room_count = fields.Integer(
        string='Phòng Đang Hoạt Động',
        compute='_compute_meeting_room_count',
        store=True
    )

    @api.depends('event_type_id.allow_community', 'event_type_id.allow_room_creation')
    def _compute_community_settings(self):
        """Inherit settings from event type"""
        for event in self:
            if event.event_type_id:
                event.allow_community = event.event_type_id.allow_community
                event.allow_room_creation = event.event_type_id.allow_room_creation
            else:
                event.allow_community = False
                event.allow_room_creation = False

    @api.depends('meeting_room_ids', 'meeting_room_ids.active')
    def _compute_meeting_room_count(self):
        """Count total and active rooms"""
        for event in self:
            rooms = event.meeting_room_ids
            event.meeting_room_count = len(rooms)
            event.active_room_count = len(rooms.filtered(lambda r: r.active and not r.is_closed))

    def action_view_meeting_rooms(self):
        """Open meeting rooms list"""
        self.ensure_one()
        return {
            'name': _('Phòng Họp'),
            'type': 'ir.actions.act_window',
            'res_model': 'event.meeting.room',
            'view_mode': 'tree,form',
            'domain': [('event_id', '=', self.id)],
            'context': {
                'default_event_id': self.id,
                'default_max_capacity': self.event_type_id.default_room_capacity or 50,
            },
        }

    def action_view_room_statistics(self):
        """Open room statistics"""
        self.ensure_one()
        return {
            'name': _('Thống Kê Phòng - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'event.meeting.room',
            'view_mode': 'pivot,graph,tree',
            'domain': [('event_id', '=', self.id)],
            'context': {
                'search_default_group_by_language': 1,
                'search_default_active': 1,
            },
        }
