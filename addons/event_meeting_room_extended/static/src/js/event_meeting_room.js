odoo.define('event_meeting_room_extended.meeting_room', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    // Jitsi Integration
    publicWidget.registry.EventMeetingRoom = publicWidget.Widget.extend({
        selector: '#jitsi_meet',
        
        start: function () {
            var self = this;
            var $el = this.$el;
            
            // Get room info from data attributes
            var roomId = parseInt($el.data('room-id'));
            var roomName = $el.data('room-name');
            var userName = $el.data('user-name') || 'Guest';
            
            if (!roomName) {
                console.error('No room name specified');
                return this._super.apply(this, arguments);
            }
            
            // Load Jitsi API
            if (typeof JitsiMeetExternalAPI === 'undefined') {
                $.getScript('https://meet.jit.si/external_api.js').then(function() {
                    self._initJitsi(roomName, userName, roomId);
                });
            } else {
                this._initJitsi(roomName, userName, roomId);
            }
            
            return this._super.apply(this, arguments);
        },
        
        _initJitsi: function (roomName, userName, roomId) {
            var self = this;
            var domain = 'meet.jit.si'; // Can be configured
            
            var options = {
                roomName: roomName,
                width: '100%',
                height: '100%',
                parentNode: this.el,
                userInfo: {
                    displayName: userName
                },
                configOverwrite: {
                    startWithAudioMuted: true,
                    startWithVideoMuted: false,
                    enableWelcomePage: false,
                },
                interfaceConfigOverwrite: {
                    SHOW_JITSI_WATERMARK: false,
                    SHOW_WATERMARK_FOR_GUESTS: false,
                    DEFAULT_BACKGROUND: '#474747',
                    TOOLBAR_BUTTONS: [
                        'microphone', 'camera', 'desktop', 'fullscreen',
                        'fodeviceselection', 'hangup', 'profile', 'chat',
                        'recording', 'sharedvideo', 'settings', 'raisehand',
                        'videoquality', 'filmstrip', 'stats', 'shortcuts',
                        'tileview', 'videobackgroundblur', 'help', 'mute-everyone'
                    ],
                }
            };
            
            var api = new JitsiMeetExternalAPI(domain, options);
            
            // Track join/leave events
            api.addEventListener('videoConferenceJoined', function (event) {
                self._roomJoin(roomId);
                self._logActivity(roomId, 'join', event && event.id, userName, {
                    local: true,
                });
            });
            
            api.addEventListener('videoConferenceLeft', function (event) {
                self._roomLeave(roomId);
                self._logActivity(roomId, 'leave', event && event.id, userName, {
                    local: true,
                });
            });

            api.addEventListener('participantJoined', function (event) {
                self._logActivity(roomId, 'participant_join', event && event.id, event && event.displayName, {
                    local: false,
                });
            });

            api.addEventListener('participantLeft', function (event) {
                self._logActivity(roomId, 'participant_leave', event && event.id, event && event.displayName, {
                    local: false,
                });
            });

            api.addEventListener('raiseHandUpdated', function (event) {
                var action = event && event.handRaised ? 'hand_raise' : 'hand_lower';
                self._logActivity(roomId, action, event && event.id, event && event.displayName, {
                    local: event && event.local,
                });
            });

            api.addEventListener('audioMuteStatusChanged', function (event) {
                var action = event && event.muted ? 'mute_audio' : 'unmute_audio';
                self._logActivity(roomId, action, event && event.id, event && event.displayName, {
                    local: event && event.local,
                });
            });

            api.addEventListener('videoMuteStatusChanged', function (event) {
                var action = event && event.muted ? 'mute_video' : 'unmute_video';
                self._logActivity(roomId, action, event && event.id, event && event.displayName, {
                    local: event && event.local,
                });
            });
            
            // Cleanup on page unload
            $(window).on('beforeunload', function() {
                self._roomLeave(roomId);
                self._logActivity(roomId, 'leave', null, userName, {
                    local: true,
                    reason: 'beforeunload',
                });
            });
        },
        
        _roomJoin: function (roomId) {
            return ajax.jsonRpc('/event/room/' + roomId + '/join', 'call', {})
                .then(function (result) {
                    if (result.error) {
                        console.error('Join failed:', result.error);
                    } else {
                        // Update UI
                        $('#room_participants').text(result.current_participants);
                        var max = parseInt($('#room_capacity_bar').data('max') || 0);
                        var percentage = max ? (result.current_participants / max) * 100 : 0;
                        $('#room_capacity_bar').css('width', percentage + '%');
                    }
                });
        },
        
        _roomLeave: function (roomId) {
            return ajax.jsonRpc('/event/room/' + roomId + '/leave', 'call', {})
                .then(function (result) {
                    if (result && result.current_participants !== undefined) {
                        $('#room_participants').text(result.current_participants);
                        var max = parseInt($('#room_capacity_bar').data('max') || 0);
                        var percentage = max ? (result.current_participants / max) * 100 : 0;
                        $('#room_capacity_bar').css('width', percentage + '%');
                    }
                });
        },

        _logActivity: function (roomId, action, participantId, displayName, metadata) {
            return ajax.jsonRpc('/event/room/' + roomId + '/activity', 'call', {
                action: action,
                participant_id: participantId || null,
                display_name: displayName || null,
                metadata: metadata || null,
            });
        },
    });

    // Community Page Actions
    window.togglePin = function(el) {
        var roomId = $(el).data('room-id');
        ajax.jsonRpc('/event/room/' + roomId + '/pin', 'call', {})
            .then(function (result) {
                if (result.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (result.error || 'Unknown error'));
                }
            });
    };

    window.closeRoom = function(el) {
        if (!confirm('Are you sure you want to close this room?')) {
            return;
        }
        var roomId = $(el).data('room-id');
        ajax.jsonRpc('/event/room/' + roomId + '/close', 'call', {})
            .then(function (result) {
                if (result.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (result.error || 'Unknown error'));
                }
            });
    };

    window.duplicateRoom = function(el) {
        // This would typically open a form or redirect
        var roomId = $(el).data('room-id');
        window.location.href = '/web#model=event.meeting.room&id=' + roomId + '&view_type=form&menu_id=XXX';
    };

    return publicWidget.registry.EventMeetingRoom;
});
