# -*- coding: utf-8 -*-

import json
from odoo import api, fields, models, _


class EventMeetingRoomActionLog(models.Model):
    _name = 'event.meeting.room.action.log'
    _description = 'Event Meeting Room Action Log'
    _order = 'action_time desc, id desc'

    room_id = fields.Many2one(
        'event.meeting.room',
        string='Phòng',
        required=True,
        ondelete='cascade',
        index=True
    )
    event_id = fields.Many2one(
        'event.event',
        string='Sự kiện',
        related='room_id.event_id',
        store=True,
        readonly=True
    )
    user_id = fields.Many2one('res.users', string='Người dùng', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Liên hệ', readonly=True)
    guest_name = fields.Char(string='Tên hiển thị', readonly=True)

    action = fields.Selection([
        ('join', 'Tham gia'),
        ('leave', 'Rời khỏi'),
        ('participant_join', 'Người khác tham gia'),
        ('participant_leave', 'Người khác rời'),
        ('hand_raise', 'Giơ tay'),
        ('hand_lower', 'Hạ tay'),
        ('mute_audio', 'Tắt mic'),
        ('unmute_audio', 'Bật mic'),
        ('mute_video', 'Tắt camera'),
        ('unmute_video', 'Bật camera'),
    ], string='Hành động', required=True, index=True)

    participant_id = fields.Char(string='Jitsi Participant ID', readonly=True)
    action_time = fields.Datetime(string='Thời gian', default=fields.Datetime.now, required=True, index=True)
    metadata_json = fields.Text(string='Dữ liệu bổ sung', readonly=True)

    def get_metadata(self):
        self.ensure_one()
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}
