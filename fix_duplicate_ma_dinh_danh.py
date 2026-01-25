"""
Script để fix duplicate ma_dinh_danh trong bảng nhan_vien
"""

env['nhan_vien']._cr.execute("""
    -- Tìm các ma_dinh_danh bị trùng
    SELECT ma_dinh_danh, array_agg(id) as ids, count(*) as count
    FROM nhan_vien
    GROUP BY ma_dinh_danh
    HAVING count(*) > 1
""")

duplicates = env['nhan_vien']._cr.fetchall()

if duplicates:
    print(f"Tìm thấy {len(duplicates)} ma_dinh_danh bị trùng:")
    
    for ma_dinh_danh, ids, count in duplicates:
        print(f"\n  ma_dinh_danh='{ma_dinh_danh}' có {count} bản ghi: {ids}")
        
        # Giữ lại bản ghi đầu tiên, sửa các bản ghi còn lại
        for i, record_id in enumerate(ids[1:], start=2):
            record = env['nhan_vien'].browse(record_id)
            new_ma_dinh_danh = f"{ma_dinh_danh}{i}"
            
            print(f"    Sửa record ID {record_id}: '{ma_dinh_danh}' -> '{new_ma_dinh_danh}'")
            
            # Update trực tiếp trong database để tránh trigger compute fields
            env['nhan_vien']._cr.execute("""
                UPDATE nhan_vien 
                SET ma_dinh_danh = %s 
                WHERE id = %s
            """, (new_ma_dinh_danh, record_id))
    
    env.cr.commit()
    print("\n✓ Đã fix xong các ma_dinh_danh trùng lặp")
else:
    print("✓ Không có ma_dinh_danh nào bị trùng")

print("\nBây giờ bạn có thể upgrade module nhan_su để áp dụng unique constraint")
