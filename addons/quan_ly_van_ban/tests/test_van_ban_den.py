# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestVanBanDen(TransactionCase):

    def setUp(self):
        super(TestVanBanDen, self).setUp()
        self.employee_a = self.env['nhan_vien'].create({
            'ma_dinh_danh': 'NV001',
            'ho_ten_dem': 'Nguyen',
            'ten': 'A',
            'ngay_sinh': '1990-01-01',
        })
        self.employee_b = self.env['nhan_vien'].create({
            'ma_dinh_danh': 'NV002',
            'ho_ten_dem': 'Tran',
            'ten': 'B',
            'ngay_sinh': '1990-01-01',
        })

    def test_van_ban_den_count(self):
        # Tạo văn bản cho employee_a
        van_ban = self.env['van_ban_den'].create({
            'so_van_ban_den': 'VB001',
            'ten_van_ban': 'Văn bản 1',
            'so_hieu_van_ban': 'SH001',
            'noi_gui_den': 'Noi gui',
            'handler_employee_id': self.employee_a.id,
        })
        self.assertEqual(self.employee_a.van_ban_den_count, 1)
        self.assertEqual(self.employee_b.van_ban_den_count, 0)

        # Tạo thêm văn bản
        van_ban2 = self.env['van_ban_den'].create({
            'so_van_ban_den': 'VB002',
            'ten_van_ban': 'Văn bản 2',
            'so_hieu_van_ban': 'SH002',
            'noi_gui_den': 'Noi gui',
            'handler_employee_id': self.employee_a.id,
        })
        self.employee_a._compute_van_ban_den_count()
        self.assertEqual(self.employee_a.van_ban_den_count, 2)

    def test_action_view_van_ban_den(self):
        action = self.employee_a.action_view_van_ban_den()
        self.assertEqual(action['res_model'], 'van_ban_den')
        self.assertEqual(action['domain'], [('handler_employee_id', '=', self.employee_a.id)])
        self.assertEqual(action['context']['default_handler_employee_id'], self.employee_a.id)