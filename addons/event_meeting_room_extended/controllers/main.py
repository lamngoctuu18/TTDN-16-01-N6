# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError
from odoo.addons.website.controllers.main import QueryURL
from datetime import datetime, timedelta


class EventCommunityController(http.Controller):

    @http.route(['/event/<model("event.event"):event>/community'], type='http', auth='public', website=True, sitemap=False)
    def event_community(self, event, lang=None, **kwargs):
        """Community page with meeting rooms list"""
        
        # Check if community is enabled
        if not event.allow_community:
            return request.redirect('/event/%s' % event.id)
        
        # Check access
        try:
            event.check_access_rights('read')
            event.check_access_rule('read')
        except AccessError:
            return request.redirect('/event/%s' % event.id)
        
        # Get available languages
        languages = request.env['res.lang'].search([('active', '=', True)])
        selected_lang = None
        if lang:
            selected_lang = languages.filtered(lambda l: l.code == lang)
        
        # Build domain
        domain = [
            ('event_id', '=', event.id),
            ('active', '=', True),
        ]
        
        # Filter by language
        if selected_lang:
            domain.append(('language_id', '=', selected_lang.id))
        
        # Public users only see published rooms
        if request.env.user._is_public():
            domain.extend([
                ('is_published', '=', True),
                ('is_closed', '=', False),
                ('is_full', '=', False),
            ])
        
        # Get rooms with priority: published > pinned > active
        MeetingRoom = request.env['event.meeting.room']
        rooms = MeetingRoom.search(domain)
        
        # Check if user can create rooms
        can_create_room = False
        if not request.env.user._is_public():
            # Admin can always create
            can_create_room = request.env.user.has_group('event.group_event_manager')
            
            # Check if event allows room creation
            if not can_create_room and event.allow_room_creation:
                # Check if event is ongoing or starting today
                now = datetime.now()
                event_date = event.date_begin
                if event_date:
                    # Allow if event is ongoing or starting within 24h
                    can_create_room = (
                        event_date <= now <= event.date_end or
                        (event_date - now).total_seconds() <= 86400  # 24 hours
                    )
        
        values = {
            'event': event,
            'rooms': rooms,
            'languages': languages,
            'selected_lang': selected_lang,
            'can_create_room': can_create_room,
            'is_event_manager': request.env.user.has_group('event.group_event_manager'),
        }
        
        return request.render('event_meeting_room_extended.event_community_page', values)

    @http.route(['/event/<model("event.event"):event>/room/create'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def create_meeting_room(self, event, **post):
        """Create a new meeting room"""
        
        # Check if community is enabled
        if not event.allow_community:
            return request.redirect('/event/%s' % event.id)
        
        # Check if room creation is allowed
        if not event.allow_room_creation and not request.env.user.has_group('event.group_event_manager'):
            return request.redirect('/event/%s/community' % event.id)
        
        # Validate inputs
        name = post.get('name', '').strip()
        if not name:
            return request.redirect('/event/%s/community?error=name_required' % event.id)
        
        # Create room
        values = {
            'event_id': event.id,
            'name': name,
            'summary': post.get('summary', '').strip(),
            'target_audience': post.get('target_audience', 'all'),
            'max_capacity': int(post.get('max_capacity', event.event_type_id.default_room_capacity or 50)),
            'is_published': True,
        }
        
        # Language
        language_code = post.get('language')
        if language_code:
            language = request.env['res.lang'].search([('code', '=', language_code)], limit=1)
            if language:
                values['language_id'] = language.id
        
        try:
            room = request.env['event.meeting.room'].create(values)
            return request.redirect('/event/%s/room/%s' % (event.id, room.room_token))
        except Exception as e:
            return request.redirect('/event/%s/community?error=creation_failed' % event.id)

    @http.route(['/event/<model("event.event"):event>/room/<string:token>'], type='http', auth='public', website=True, sitemap=False)
    def event_meeting_room_page(self, event, token, **kwargs):
        """Meeting room page with Jitsi embed"""
        
        # Find room
        room = request.env['event.meeting.room'].search([
            ('event_id', '=', event.id),
            ('room_token', '=', token),
        ], limit=1)
        
        if not room:
            return request.not_found()
        
        # Check access
        if room.is_published or request.env.user.has_group('event.group_event_user'):
            pass
        else:
            return request.redirect('/event/%s/community' % event.id)
        
        # Check if user is registered for event (for non-public users)
        is_registered = False
        current_user = request.env.user
        if not current_user._is_public():
            registration = request.env['event.registration'].search([
                ('event_id', '=', event.id),
                ('partner_id', '=', current_user.partner_id.id),
                ('state', 'in', ['open', 'done']),
            ], limit=1)
            is_registered = bool(registration)
        
        # Get other rooms (sidebar)
        other_rooms_domain = [
            ('event_id', '=', event.id),
            ('id', '!=', room.id),
            ('active', '=', True),
            ('is_published', '=', True),
            ('is_closed', '=', False),
        ]
        if request.env.user._is_public():
            other_rooms_domain.append(('is_full', '=', False))
        
        other_rooms = request.env['event.meeting.room'].search(other_rooms_domain, limit=5)
        
        # Check event timing
        now = datetime.now()
        event_started = event.date_begin <= now if event.date_begin else True
        event_ended = event.date_end < now if event.date_end else False
        
        values = {
            'event': event,
            'room': room,
            'other_rooms': other_rooms,
            'is_registered': is_registered,
            'is_public_user': current_user._is_public(),
            'event_started': event_started,
            'event_ended': event_ended,
            'can_join': (
                not room.is_closed and
                not room.is_full and
                event_started and
                not event_ended
            ),
        }
        
        return request.render('event_meeting_room_extended.event_meeting_room_page', values)

    @http.route(['/event/room/<int:room_id>/join'], type='json', auth='user', website=True)
    def room_join(self, room_id, **kwargs):
        """Join a room (increment counter)"""
        room = request.env['event.meeting.room'].browse(room_id)
        
        if not room.exists():
            return {'error': 'Room not found'}
        
        if room.is_closed:
            return {'error': 'Room is closed'}
        
        if room.is_full:
            return {'error': 'Room is full'}
        
        try:
            room.join_room()
            return {'success': True, 'current_participants': room.current_participants}
        except Exception as e:
            return {'error': str(e)}

    @http.route(['/event/room/<int:room_id>/leave'], type='json', auth='user', website=True)
    def room_leave(self, room_id, **kwargs):
        """Leave a room (decrement counter)"""
        room = request.env['event.meeting.room'].browse(room_id)
        
        if not room.exists():
            return {'error': 'Room not found'}
        
        try:
            room.leave_room()
            return {'success': True, 'current_participants': room.current_participants}
        except Exception as e:
            return {'error': str(e)}

    @http.route(['/event/room/<int:room_id>/pin'], type='json', auth='user', website=True)
    def room_pin(self, room_id, **kwargs):
        """Pin/unpin room (admin only)"""
        if not request.env.user.has_group('event.group_event_manager'):
            return {'error': 'Permission denied'}
        
        room = request.env['event.meeting.room'].browse(room_id)
        if not room.exists():
            return {'error': 'Room not found'}
        
        room.is_pinned = not room.is_pinned
        return {'success': True, 'is_pinned': room.is_pinned}

    @http.route(['/event/room/<int:room_id>/close'], type='json', auth='user', website=True)
    def room_close(self, room_id, **kwargs):
        """Close/reopen room (admin only)"""
        if not request.env.user.has_group('event.group_event_manager'):
            return {'error': 'Permission denied'}
        
        room = request.env['event.meeting.room'].browse(room_id)
        if not room.exists():
            return {'error': 'Room not found'}
        
        room.is_closed = not room.is_closed
        return {'success': True, 'is_closed': room.is_closed}
