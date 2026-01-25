# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AIAssetWizard(models.TransientModel):
    """Wizard cho các tính năng AI với Tài sản"""
    _name = 'ai.asset.wizard'
    _description = 'AI Asset Wizard'
    
    action_type = fields.Selection([
        ('qa', 'Hỏi đáp về tài sản'),
        ('maintenance', 'Gợi ý bảo trì'),
        ('risk', 'Phân tích rủi ro'),
    ], string='Loại hành động', required=True, default='qa')
    
    # For Q&A
    question = fields.Text(string='Câu hỏi của bạn')
    
    # For Maintenance suggestion
    asset_id = fields.Many2one('dnu.asset', string='Tài sản')
    
    # For Risk analysis
    asset_ids = fields.Many2many(
        'dnu.asset',
        string='Tài sản phân tích',
        help='Để trống để phân tích tất cả'
    )
    
    # Result
    result = fields.Html(string='Kết quả', readonly=True)
    show_result = fields.Boolean(default=False)
    
    def action_execute(self):
        """Thực thi AI action"""
        self.ensure_one()
        service = self.env['openai.service']
        
        try:
            if self.action_type == 'qa':
                if not self.question:
                    raise UserError(_('Vui lòng nhập câu hỏi.'))
                
                asset_ids = self.asset_ids.ids if self.asset_ids else None
                result = service.asset_qa(self.question, asset_ids)
                
                self.result = f"""
                <div class="ai-result">
                    <h4>🤖 Trả lời từ AI:</h4>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{result['answer']}
                    </div>
                    <small class="text-muted">Model: {result['model']} | {result['timestamp']}</small>
                </div>
                """
                
            elif self.action_type == 'maintenance':
                if not self.asset_id:
                    raise UserError(_('Vui lòng chọn tài sản.'))
                
                result = service.suggest_maintenance(self.asset_id.id)
                
                self.result = f"""
                <div class="ai-result">
                    <h4>🔧 Gợi ý bảo trì cho {result['asset_code']} - {result['asset_name']}:</h4>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{result['suggestions']}
                    </div>
                    <small class="text-muted">{result['timestamp']}</small>
                </div>
                """
                
            elif self.action_type == 'risk':
                asset_ids = self.asset_ids.ids if self.asset_ids else None
                result = service.analyze_asset_risk(asset_ids)
                
                summary = result['summary']
                self.result = f"""
                <div class="ai-result">
                    <h4>⚠️ Phân tích rủi ro tài sản:</h4>
                    <div class="summary-stats" style="background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>Tổng quan:</strong><br/>
                        - Tổng số tài sản: {summary['total_assets']}<br/>
                        - Tài sản cũ (>5 năm): {len(summary['old_assets'])}<br/>
                        - Tài sản giá trị cao (>50M): {len(summary['high_value'])}<br/>
                        - Bảo trì thường xuyên (>5 lần): {len(summary['frequent_maintenance'])}
                    </div>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{result['analysis']}
                    </div>
                    <small class="text-muted">{result['timestamp']}</small>
                </div>
                """
            
            self.show_result = True
            
        except Exception as e:
            self.result = f"""
            <div class="alert alert-danger">
                <strong>Lỗi:</strong> {str(e)}
            </div>
            """
            self.show_result = True
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ai.asset.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class AIMeetingWizard(models.TransientModel):
    """Wizard cho các tính năng AI với Phòng họp"""
    _name = 'ai.meeting.wizard'
    _description = 'AI Meeting Wizard'
    
    action_type = fields.Selection([
        ('summary', 'Tạo biên bản họp'),
        ('schedule', 'Gợi ý thời gian họp'),
        ('agenda', 'Tạo agenda cuộc họp'),
        ('chat', 'Chat với AI'),
    ], string='Loại hành động', required=True, default='chat')
    
    # For Summary
    booking_id = fields.Many2one('dnu.meeting.booking', string='Cuộc họp')
    meeting_notes = fields.Text(string='Ghi chú cuộc họp', help='Thêm ghi chú để tạo biên bản chi tiết hơn')
    
    # For Schedule suggestion
    attendee_ids = fields.Many2many(
        'hr.employee',
        string='Người tham dự'
    )
    duration_hours = fields.Float(string='Thời lượng (giờ)', default=1.0)
    preferred_date = fields.Date(string='Ngày ưu tiên')
    
    # For Agenda
    meeting_subject = fields.Char(string='Chủ đề cuộc họp')
    meeting_description = fields.Text(string='Mô tả cuộc họp')
    
    # For Chat
    chat_message = fields.Text(string='Tin nhắn')
    
    # Result
    result = fields.Html(string='Kết quả', readonly=True)
    show_result = fields.Boolean(default=False)
    
    @api.onchange('booking_id')
    def _onchange_booking_id(self):
        if self.booking_id:
            self.meeting_notes = self.booking_id.notes
            self.meeting_subject = self.booking_id.subject
            self.meeting_description = self.booking_id.description
            self.duration_hours = self.booking_id.duration or 1.0
            self.attendee_ids = self.booking_id.attendee_ids
    
    def action_execute(self):
        """Thực thi AI action"""
        self.ensure_one()
        service = self.env['openai.service']
        
        try:
            if self.action_type == 'summary':
                if not self.booking_id:
                    raise UserError(_('Vui lòng chọn cuộc họp.'))
                
                result = service.generate_meeting_summary(
                    self.booking_id.id,
                    notes=self.meeting_notes
                )
                
                self.result = f"""
                <div class="ai-result">
                    <h4>📝 Biên bản cuộc họp: {result['subject']}</h4>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace;">
{result['summary']}
                    </div>
                    <small class="text-muted">{result['timestamp']}</small>
                </div>
                """
                
            elif self.action_type == 'schedule':
                if not self.attendee_ids:
                    raise UserError(_('Vui lòng chọn người tham dự.'))
                
                result = service.suggest_meeting_time(
                    self.attendee_ids.ids,
                    self.duration_hours,
                    self.preferred_date
                )
                
                self.result = f"""
                <div class="ai-result">
                    <h4>📅 Gợi ý thời gian họp</h4>
                    <div class="info" style="background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>Người tham dự:</strong> {', '.join(result['attendees'])}<br/>
                        <strong>Thời lượng:</strong> {result['duration']} giờ<br/>
                        <strong>Khoảng thời gian:</strong> {result['date_range']}
                    </div>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{result['suggestions']}
                    </div>
                    <small class="text-muted">{result['timestamp']}</small>
                </div>
                """
                
            elif self.action_type == 'agenda':
                if not self.meeting_subject:
                    raise UserError(_('Vui lòng nhập chủ đề cuộc họp.'))
                
                result = service.generate_meeting_agenda(
                    self.meeting_subject,
                    self.meeting_description,
                    self.duration_hours
                )
                
                self.result = f"""
                <div class="ai-result">
                    <h4>📋 Agenda cuộc họp: {result['subject']}</h4>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{result['agenda']}
                    </div>
                    <small class="text-muted">{result['timestamp']}</small>
                </div>
                """
                
            elif self.action_type == 'chat':
                if not self.chat_message:
                    raise UserError(_('Vui lòng nhập tin nhắn.'))
                
                response = service.chat(self.chat_message)
                
                self.result = f"""
                <div class="ai-result">
                    <h4>💬 AI Assistant</h4>
                    <div class="user-message" style="background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>Bạn:</strong> {self.chat_message}
                    </div>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{response}
                    </div>
                </div>
                """
            
            self.show_result = True
            
        except Exception as e:
            self.result = f"""
            <div class="alert alert-danger">
                <strong>Lỗi:</strong> {str(e)}
            </div>
            """
            self.show_result = True
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ai.meeting.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class AIHRWizard(models.TransientModel):
    """Wizard cho các tính năng AI với Nhân sự"""
    _name = 'ai.hr.wizard'
    _description = 'AI HR Wizard'
    
    action_type = fields.Selection([
        ('chat', 'Trò chuyện về nhân sự'),
        ('department_analysis', 'Phân tích phòng ban'),
        ('employee_search', 'Tìm kiếm nhân viên'),
    ], string='Loại hành động', required=True, default='chat')
    
    # For Chat
    message = fields.Text(string='Câu hỏi')
    
    # For Department Analysis
    department_id = fields.Many2one('don_vi', string='Phòng ban')
    
    # For Employee Search
    search_criteria = fields.Char(string='Tiêu chí tìm kiếm')
    
    # Result
    result = fields.Html(string='Kết quả', readonly=True)
    show_result = fields.Boolean(default=False)
    
    def action_execute(self):
        """Thực thi AI action"""
        self.ensure_one()
        service = self.env['openai.service']
        
        try:
            if self.action_type == 'chat':
                if not self.message:
                    raise UserError(_('Vui lòng nhập câu hỏi.'))
                
                context = "Người dùng đang hỏi về quản lý nhân sự."
                response = service.chat(self.message, context)
                
                self.result = f"""
                <div class="ai-result">
                    <h4>🤖 AI Assistant</h4>
                    <div class="user-message" style="background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>Bạn:</strong> {self.message}
                    </div>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{response}
                    </div>
                </div>
                """
                
            elif self.action_type == 'department_analysis':
                if not self.department_id:
                    raise UserError(_('Vui lòng chọn phòng ban.'))
                
                message = f"Phân tích tổng quan về phòng ban {self.department_id.ten_don_vi}"
                context = "Người dùng muốn phân tích chi tiết về một phòng ban cụ thể."
                response = service.chat(message, context)
                
                self.result = f"""
                <div class="ai-result">
                    <h4>📊 Phân tích phòng ban: {self.department_id.ten_don_vi}</h4>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{response}
                    </div>
                </div>
                """
                
            elif self.action_type == 'employee_search':
                if not self.search_criteria:
                    raise UserError(_('Vui lòng nhập tiêu chí tìm kiếm.'))
                
                message = f"Tìm nhân viên theo tiêu chí: {self.search_criteria}"
                context = "Người dùng muốn tìm kiếm thông tin nhân viên."
                response = service.chat(message, context)
                
                self.result = f"""
                <div class="ai-result">
                    <h4>🔍 Kết quả tìm kiếm</h4>
                    <div class="search-criteria" style="background: #e3f2fd; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>Tiêu chí:</strong> {self.search_criteria}
                    </div>
                    <div class="ai-answer" style="white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px;">
{response}
                    </div>
                </div>
                """
            
            self.show_result = True
            
        except Exception as e:
            self.result = f"""
            <div class="alert alert-danger">
                <strong>Lỗi:</strong> {str(e)}
            </div>
            """
            self.show_result = True
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ai.hr.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
