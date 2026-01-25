# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class EventType(models.Model):
    _inherit = 'event.type'

    # Community settings
    allow_community = fields.Boolean(
        string='Bật Cộng Đồng',
        default=False,
        help='Cho phép trang cộng đồng với phòng họp cho các sự kiện thuộc loại này'
    )
    allow_room_creation = fields.Boolean(
        string='Cho Phép Tạo Phòng',
        default=True,
        help='Cho phép người tham gia tạo phòng họp của riêng họ'
    )
    auto_room_creation = fields.Boolean(
        string='Tự Động Tạo Phòng Mặc Định',
        default=False,
        help='Tự động tạo phòng họp mặc định khi sự kiện được xuất bản'
    )
    default_room_capacity = fields.Integer(
        string='Sức Chứa Phòng Mặc Định',
        default=50,
        help='Sức chứa tối đa mặc định cho phòng mới'
    )
    room_auto_archive_hours = fields.Integer(
        string='Số Giờ Tự Động Lưu Trữ',
        default=4,
        help='Lưu trữ các phòng không hoạt động sau số giờ này (trừ phòng đã ghim)'
    )
