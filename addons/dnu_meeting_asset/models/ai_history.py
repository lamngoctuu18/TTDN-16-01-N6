# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AISession(models.Model):
    _name = 'ai.session'
    _description = 'AI Session'
    _order = 'last_activity_at desc, create_date desc'

    name = fields.Char(string='Tên phiên', required=True, default=lambda self: _('AI Session'))
    context_model = fields.Char(string='Model liên quan', index=True)
    context_res_id = fields.Integer(string='ID bản ghi', index=True)
    context_display_name = fields.Char(string='Bản ghi liên quan', compute='_compute_context_display_name', store=True)
    channel = fields.Selection([
        ('asset', 'AI Tài sản'),
        ('meeting', 'AI Phòng họp'),
        ('hr', 'AI Nhân sự'),
        ('general', 'Chung'),
    ], string='Kênh', default='general', index=True)
    owner_id = fields.Many2one('res.users', string='Người tạo', default=lambda self: self.env.user, required=True)
    request_ids = fields.One2many('ai.request', 'session_id', string='Lượt hỏi')
    request_count = fields.Integer(string='Số lượt hỏi', compute='_compute_request_count')
    last_activity_at = fields.Datetime(string='Lần hoạt động cuối')

    _sql_constraints = [
        ('uniq_ai_session_context', 'unique(context_model, context_res_id)', 'Mỗi bản ghi chỉ có một session AI.'),
    ]

    @api.depends('context_model', 'context_res_id')
    def _compute_context_display_name(self):
        for rec in self:
            if rec.context_model and rec.context_res_id:
                record = self.env[rec.context_model].browse(rec.context_res_id)
                rec.context_display_name = record.display_name if record.exists() else False
            else:
                rec.context_display_name = False

    @api.depends('request_ids')
    def _compute_request_count(self):
        for rec in self:
            rec.request_count = len(rec.request_ids)

    @api.model
    def get_or_create_session(self, context_model, context_res_id, channel=None):
        if not context_model or not context_res_id:
            return False

        session = self.search([
            ('context_model', '=', context_model),
            ('context_res_id', '=', context_res_id),
        ], limit=1)

        if session:
            if channel and session.channel != channel:
                session.channel = channel
            return session

        display_name = None
        record = self.env[context_model].browse(context_res_id)
        if record.exists():
            display_name = record.display_name

        session_name = display_name or _('AI Session')

        return self.create({
            'name': session_name,
            'context_model': context_model,
            'context_res_id': context_res_id,
            'channel': channel or 'general',
            'owner_id': self.env.user.id,
            'last_activity_at': fields.Datetime.now(),
        })


class AIRequest(models.Model):
    _name = 'ai.request'
    _description = 'AI Request'
    _order = 'create_date desc'

    name = fields.Char(string='Tiêu đề', default=lambda self: _('AI Request'))
    session_id = fields.Many2one('ai.session', string='Phiên AI', ondelete='set null')
    context_model = fields.Char(string='Model liên quan', index=True)
    context_res_id = fields.Integer(string='ID bản ghi', index=True)
    context_display_name = fields.Char(string='Bản ghi liên quan', compute='_compute_context_display_name', store=True)
    channel = fields.Selection([
        ('asset', 'AI Tài sản'),
        ('meeting', 'AI Phòng họp'),
        ('hr', 'AI Nhân sự'),
        ('general', 'Chung'),
    ], string='Kênh', default='general', index=True)
    intent = fields.Char(string='Mục đích', index=True)

    user_id = fields.Many2one('res.users', string='Người hỏi', default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company, required=True)

    prompt = fields.Text(string='Prompt')
    response = fields.Text(string='Response')
    response_html = fields.Html(string='Response (HTML)')

    status = fields.Selection([
        ('success', 'Thành công'),
        ('error', 'Lỗi'),
        ('canceled', 'Đã hủy'),
    ], string='Trạng thái', default='success', index=True)
    error_message = fields.Text(string='Lỗi chi tiết')

    model_name = fields.Char(string='Model')
    provider = fields.Char(string='Provider', default='openai')
    latency_ms = fields.Integer(string='Độ trễ (ms)')
    token_in = fields.Integer(string='Token vào')
    token_out = fields.Integer(string='Token ra')
    cost_estimate = fields.Float(string='Ước tính chi phí')

    rating = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Đánh giá')
    feedback = fields.Text(string='Góp ý')

    @api.depends('context_model', 'context_res_id')
    def _compute_context_display_name(self):
        for rec in self:
            if rec.context_model and rec.context_res_id:
                record = self.env[rec.context_model].browse(rec.context_res_id)
                rec.context_display_name = record.display_name if record.exists() else False
            else:
                rec.context_display_name = False

    @api.model
    def log_request(
        self,
        context_model,
        context_res_id,
        channel,
        intent,
        prompt,
        response=None,
        response_html=None,
        status='success',
        error_message=None,
        model_name=None,
        provider='openai',
        latency_ms=None,
        token_in=None,
        token_out=None,
        cost_estimate=None,
    ):
        session = self.env['ai.session'].get_or_create_session(context_model, context_res_id, channel)

        name = intent or _('AI Request')
        if context_model and context_res_id:
            record = self.env[context_model].browse(context_res_id)
            if record.exists():
                name = f"{name} - {record.display_name}"

        request = self.create({
            'name': name,
            'session_id': session.id if session else False,
            'context_model': context_model,
            'context_res_id': context_res_id,
            'channel': channel or 'general',
            'intent': intent,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'prompt': prompt,
            'response': response,
            'response_html': response_html,
            'status': status,
            'error_message': error_message,
            'model_name': model_name,
            'provider': provider,
            'latency_ms': latency_ms,
            'token_in': token_in,
            'token_out': token_out,
            'cost_estimate': cost_estimate,
        })

        if session:
            session.last_activity_at = fields.Datetime.now()

        return request
