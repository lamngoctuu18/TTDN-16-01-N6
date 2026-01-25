"""
Test script để kiểm tra so_nguoi_bang_tuoi compute đúng
"""

# Tìm nhân viên có cùng tuổi
employees = env['nhan_vien'].search([])

print("\n=== KIỂM TRA SỐ NGƯỜI BẰNG TUỔI ===\n")
print(f"Tổng số nhân viên: {len(employees)}\n")

# Group by tuổi
from collections import defaultdict
tuoi_groups = defaultdict(list)

for emp in employees:
    if emp.tuoi:
        tuoi_groups[emp.tuoi].append(emp)

# Hiển thị các nhóm tuổi có > 1 người
print("Các nhóm tuổi có nhiều người:\n")
for tuoi in sorted(tuoi_groups.keys()):
    if len(tuoi_groups[tuoi]) > 1:
        print(f"  Tuổi {tuoi}: {len(tuoi_groups[tuoi])} người")
        for emp in tuoi_groups[tuoi]:
            print(f"    - {emp.ho_va_ten} (ma_dinh_danh={emp.ma_dinh_danh}, so_nguoi_bang_tuoi={emp.so_nguoi_bang_tuoi})")
        print()

# Recompute tất cả để đảm bảo giá trị đúng
print("\nRecompute lại tất cả so_nguoi_bang_tuoi...")
env['nhan_vien']._fields['so_nguoi_bang_tuoi'].compute_value(employees)
env.cr.commit()

print("\n=== KẾT QUẢ SAU KHI RECOMPUTE ===\n")

# Check lại
employees = env['nhan_vien'].search([])
for tuoi in sorted(tuoi_groups.keys()):
    if len(tuoi_groups[tuoi]) > 1:
        print(f"Tuổi {tuoi}:")
        for emp_old in tuoi_groups[tuoi]:
            emp = env['nhan_vien'].browse(emp_old.id)
            print(f"  - {emp.ho_va_ten}: so_nguoi_bang_tuoi = {emp.so_nguoi_bang_tuoi} (expected: {len(tuoi_groups[tuoi]) - 1})")

print("\n✓ Hoàn tất kiểm tra!")
