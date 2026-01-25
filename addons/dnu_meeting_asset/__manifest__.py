# -*- coding: utf-8 -*-
{
    'name': "Quản lý Tài sản & Phòng họp",

    'summary': """
        Quản lý tài sản công ty và điều phối lịch sử dụng phòng họp""",

    'description': """
Quản lý Tài sản & Phòng họp - DNU Meeting Asset Management

Tính năng chính:
================

📦 QUẢN LÝ TÀI SẢN:
- Quản lý tài sản công ty (thiết bị, máy móc, đồ dùng văn phòng)
- Phân loại tài sản theo danh mục
- Theo dõi lịch sử gán tài sản cho nhân viên
- Quản lý mượn/trả tài sản dùng chung (máy chiếu, laptop dự phòng...)
- Quản lý bảo trì và sửa chữa tài sản
- Lịch bảo trì định kỳ tự động
- Theo dõi giá trị tài sản và khấu hao

💰 KHẤU HAO TÀI SẢN:
- Quản lý khấu hao theo phương pháp đường thẳng hoặc số dư giảm dần
- Tự động tính khấu hao hàng tháng
- Theo dõi giá trị sổ sách và giá trị còn lại
- Báo cáo khấu hao chi tiết

📋 KIỂM KÊ TÀI SẢN:
- Tạo đợt kiểm kê định kỳ hoặc đột xuất
- Kiểm kê theo danh mục, phòng ban, vị trí
- Theo dõi tiến độ kiểm kê
- Báo cáo tình trạng tài sản: tìm thấy, mất, hỏng

🔄 LUÂN CHUYỂN TÀI SẢN:
- Luân chuyển giữa nhân viên, phòng ban, vị trí
- Quy trình phê duyệt luân chuyển
- Biên bản bàn giao tài sản
- Theo dõi lịch sử luân chuyển

♻️ THANH LÝ TÀI SẢN:
- Quản lý quy trình thanh lý (bán, tặng, hủy...)
- Tính toán lãi/lỗ thanh lý
- Phê duyệt đề xuất thanh lý
- Thanh lý hàng loạt

🏢 QUẢN LÝ PHÒNG HỌP:
- Quản lý danh sách phòng họp và trang thiết bị
- Đặt phòng họp với kiểm tra xung đột tự động
- Wizard đặt phòng nhanh với gợi ý phòng phù hợp
- Check-in/Check-out phòng họp
- Tích hợp với Calendar

📧 THÔNG BÁO:
- Gửi thông báo email xác nhận đặt phòng
- Nhắc nhở trước cuộc họp
- Cảnh báo tài sản quá hạn trả
- Thông báo bảo trì sắp đến hạn

📊 BÁO CÁO & DASHBOARD:
- Dashboard tổng quan tài sản & mượn trả
- Thống kê tài sản theo danh mục, phòng ban
- Xu hướng mượn trả theo tháng
- Báo cáo bảo trì & chi phí
- Báo cáo khấu hao
- Xuất PDF các loại biên bản

🔌 API:
- REST API cho ứng dụng di động
- Endpoints cho tích hợp hệ thống

Phát triển bởi: Nhóm Sinh viên FIT-DNU
    """,

    'author': "FIT-DNU",
    'website': "https://ttdn1501.aiotlabdnu.xyz/web",

    'category': 'Operations/Facility',
    'version': '1.1.0',

    # Dependencies
    'depends': ['base', 'hr', 'nhan_su', 'calendar', 'mail', 'board', 'quan_ly_van_ban'],

    # External dependencies
    'external_dependencies': {
        'python': ['requests'],
    },

    # Data files
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/res_users_data.xml',
        'data/sequence_data.xml',
        'data/disposal_rule_data.xml',
        'data/mail_template.xml',
        'data/cron.xml',
        'data/integration_data.xml',
        'data/openai_data.xml',
        
        # Wizards
        'wizards/wizard_views.xml',
        
        # Views - Assets
        'views/dnu_asset_views.xml',
        'views/dnu_asset_category_views.xml',
        'views/dnu_asset_assignment_views.xml',
        'views/dnu_asset_maintenance_views.xml',
        'views/dnu_asset_lending_views.xml',
        'views/dnu_asset_handover_views.xml',  # Biên bản bàn giao
        'views/dnu_asset_center_views.xml',  # Asset Center Dashboard
        'views/dnu_maintenance_schedule_views.xml',
        'views/dnu_asset_depreciation_views.xml',
        'views/dnu_asset_inventory_views.xml',
        'views/dnu_asset_transfer_views.xml',
        'views/dnu_asset_disposal_views.xml',
        'views/dnu_asset_disposal_rule_views.xml',
        
        # Views - Meeting
        'views/dnu_meeting_room_views.xml',
        'views/dnu_meeting_booking_views.xml',

        # Views - Văn bản đến (integration)
        'views/van_ban_den_inherit_views.xml',

        # Views - User guide
        'views/user_guide_views.xml',
        
        # Views - Integrations
        'views/integration_views.xml',
        'views/oauth_templates.xml',
        'views/openai_views.xml',
        'views/ai_integration_views.xml',
        
        # Views - HR Integration
        'views/hr_employee_views.xml',
        
        # Views - Automation
        'views/dnu_asset_automation_views.xml',
        
        # Reports (actions used by menus)
        'reports/asset_reports.xml',
        'reports/booking_reports.xml',

        # Views - Dashboard
        'views/dnu_asset_dashboard_views.xml',
        
        # Menu
        'views/menu_views.xml',
    ],

    # Demo data
    # 'demo': [
    #     'demo/demo_data.xml',
    # ],

    # Technical
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
