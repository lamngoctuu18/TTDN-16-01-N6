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
            });
            
            api.addEventListener('videoConferenceLeft', function (event) {
                self._roomLeave(roomId);
            });
            
            // Cleanup on page unload
            $(window).on('beforeunload', function() {
                self._roomLeave(roomId);
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
                        var percentage = (result.current_participants / $('#room_capacity_bar').data('max')) * 100;
                        $('#room_capacity_bar').css('width', percentage + '%');
                    }
                });
        },
        
        _roomLeave: function (roomId) {
            return ajax.jsonRpc('/event/room/' + roomId + '/leave', 'call', {});
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
