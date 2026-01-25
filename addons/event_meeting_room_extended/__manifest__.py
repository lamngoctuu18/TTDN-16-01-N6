# -*- coding: utf-8 -*-
{
    'name': 'Phòng Họp Sự Kiện Mở Rộng',
    'version': '1.0.0',
    'category': 'Marketing/Events',
    'summary': 'Phòng họp trực tuyến nâng cao cho sự kiện với tích hợp Jitsi',
    'description': """
Event Meeting Room Extended
===========================

Tính năng nâng cao cho phòng họp online trong sự kiện:

Quản lý Phòng họp:
------------------
- Tạo phòng họp online gắn với sự kiện cụ thể
- Hỗ trợ đa ngôn ngữ
- Giới hạn sức chứa
- Ghim phòng quan trọng
- URL riêng cho mỗi phòng
- Tự động archive phòng không hoạt động sau 4 giờ (trừ phòng đã ghim)

Cấu hình Sự kiện:
----------------
- Bật/tắt tính năng community cho từng loại sự kiện
- Kế thừa cấu hình từ loại sự kiện
- Thống kê số phòng họp của sự kiện
- Nút thống kê phòng trên backend form

Trang Community:
---------------
- URL: /event/<event>/community
- Lọc theo ngôn ngữ
- Ưu tiên hiển thị: published → pinned → đang hoạt động
- Khách chỉ thấy phòng chưa đầy
- Admin có menu ghim/nhân bản/đóng phòng

Tạo Phòng Frontend:
------------------
- Nút "Create a Room" (hiển thị khi sự kiện đang/sắp diễn ra hoặc là admin)
- Modal nhập: chủ đề, tóm tắt, đối tượng, ngôn ngữ, sức chứa
- Kiểm tra quyền tạo phòng theo cấu hình

Trang Phòng:
-----------
- Nhúng Jitsi meeting
- Kiểm tra sức chứa trước khi join
- Cảnh báo chưa tới giờ/đã hết giờ
- Sidebar hiển thị phòng khác
- Redirect chưa đăng ký → trang đăng ký kèm thông báo

Website Builder:
---------------
- Toggle "Allow Room Creation" để bật/tắt quyền khách tạo phòng
    """,
    'author': 'FIT-DNU',
    'website': 'https://ttdn1501.aiotlabdnu.xyz',
    'depends': [
        'event',
        'website_event',
        'website_jitsi',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/event_meeting_room_data.xml',
        'data/cron.xml',
        'views/event_type_views.xml',
        'views/event_event_views.xml',
        'views/event_meeting_room_views.xml',
        'views/event_meeting_room_templates.xml',
        'views/event_community_templates.xml',
        'views/snippets_templates.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'event_meeting_room_extended/static/src/js/event_meeting_room.js',
            'event_meeting_room_extended/static/src/css/event_meeting_room.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
