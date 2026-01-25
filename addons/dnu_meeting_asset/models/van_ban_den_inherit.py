# -*- coding: utf-8 -*-

from odoo import api, fields, models


class VanBanDen(models.Model):
    _inherit = 'van_ban_den'

    meeting_room_id = fields.Many2one(
        'dnu.meeting.room',
        string='Phòng họp',
        compute='_compute_meeting_links',
        store=True,
        index=True,
        readonly=True,
    )
    meeting_booking_id = fields.Many2one(
        'dnu.meeting.booking',
        string='Booking phòng họp',
        compute='_compute_meeting_links',
        store=True,
        index=True,
        readonly=True,
    )

    @api.depends('source_model', 'source_res_id')
    def _compute_meeting_links(self):
        Room = self.env['dnu.meeting.room']
        Booking = self.env['dnu.meeting.booking']
        for rec in self:
            rec.meeting_room_id = False
            rec.meeting_booking_id = False

            if rec.source_model == 'dnu.meeting.room' and rec.source_res_id:
                rec.meeting_room_id = Room.browse(rec.source_res_id).exists()
            elif rec.source_model == 'dnu.meeting.booking' and rec.source_res_id:
                rec.meeting_booking_id = Booking.browse(rec.source_res_id).exists()
