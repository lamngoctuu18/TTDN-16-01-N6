Event Meeting Room Extended - Module hoàn chỉnh!

Module này đã được tạo với đầy đủ các tính năng:

✅ Models:
- event.meeting.room: Phòng họp online với tất cả trường được yêu cầu
- Extend event.type: Cấu hình community cho loại sự kiện
- Extend event.event: Kế thừa cấu hình + đếm số phòng

✅ Controllers:
- /event/<event>/community: Trang community với lọc ngôn ngữ
- /event/<event>/room/create: Tạo phòng (POST)
- /event/<event>/room/<token>: Trang phòng với Jitsi
- JSON endpoints: join, leave, pin, close

✅ Views Backend:
- Form views cho Event Type, Event, Meeting Room
- Tree, Kanban views
- Search filters
- Stat buttons
- Menu

✅ Views Frontend:
- Community page template
- Room page template với Jitsi embed
- Create room modal
- Sidebar other rooms
- Website Builder snippet

✅ Features:
1. Gắn event, ngôn ngữ, sức chứa, ghim ✅
2. URL riêng với token ✅
3. Auto archive sau 4h (cron job) ✅
4. Public/portal chỉ xem published ✅
5. Cấu hình loại sự kiện ✅
6. Thống kê phòng backend ✅
7. Lọc theo ngôn ngữ, ưu tiên ✅
8. Khách chỉ thấy phòng chưa full ✅
9. Admin menu ghim/nhân bản/đóng ✅
10. Modal tạo phòng ✅
11. Kiểm tra quyền tạo ✅
12. Nhúng Jitsi ✅
13. Kiểm tra sức chứa ✅
14. Cảnh báo giờ ✅
15. Redirect chưa đăng ký ✅
16. Website Builder toggle ✅

Để cài đặt:
1. Module đã được tạo tại: addons/event_meeting_room_extended/
2. Chạy: ./odoo-bin -d btl_nhom6 -i event_meeting_room_extended
3. Hoặc cài từ Apps menu trong Odoo
