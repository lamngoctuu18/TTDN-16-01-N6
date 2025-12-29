# -*- coding: utf-8 -*-
# from odoo import http


# class QuanLyVanBan(http.Controller):
#     @http.route('/quan_ly_van_ban/quan_ly_van_ban', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/quan_ly_van_ban/quan_ly_van_ban/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('quan_ly_van_ban.listing', {
#             'root': '/quan_ly_van_ban/quan_ly_van_ban',
#             'objects': http.request.env['quan_ly_van_ban.quan_ly_van_ban'].search([]),
#         })

#     @http.route('/quan_ly_van_ban/quan_ly_van_ban/objects/<model("quan_ly_van_ban.quan_ly_van_ban"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('quan_ly_van_ban.object', {
#             'object': obj
#         })
