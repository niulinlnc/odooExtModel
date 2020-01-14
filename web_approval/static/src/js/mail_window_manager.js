odoo.define('web_approval.mail.Manager.Window', function (require) {
    var mailManagerWindow = require('mail.Manager.Window');
    var ThreadWindow = require('mail.ThreadWindow');

    mailManagerWindow.include({
        openBlankThreadWindow: function (options) {
            var blankThreadWindow = this._getBlankThreadWindow();
            if (!blankThreadWindow) {
                blankThreadWindow = new ThreadWindow(this, null, options); //xichun
                this._addThreadWindow(blankThreadWindow);
                blankThreadWindow.appendTo(this.THREAD_WINDOW_APPENDTO)
                    .then(this._repositionThreadWindows.bind(this));
            } else {
                if (blankThreadWindow.isHidden()) {
                    this._makeThreadWindowVisible(blankThreadWindow);
                } else if (blankThreadWindow.isFolded()) {
                    blankThreadWindow.toggleFold(false);
                }
            }
        },
        getDMChatFromPartnerID: function (partnerID, chatType) {
            return _.find(this._threads, function (thread) {
                return thread.getType() === chatType &&
                        thread.getDirectPartnerID() === partnerID;
            });
        },
        openDMChatWindowFromBlankThreadWindow: function (partnerID, options) {
            var chatType = 'dm_chat';
            if(options.approvalSwap){
                chatType = 'swap'
            }
            var dmChat = this.getDMChatFromPartnerID(partnerID, chatType);
            if (!dmChat) {
                this._openAndDetachDMChat(partnerID, options);
            } else {
                this.openThreadWindow(dmChat.getID());
            }
            this._closeBlankThreadWindow();
        },
        _openAndDetachDMChat: function (partnerID, options) {
            var opt = {};
            if(options.approvalSwap){
                opt = {
                    'waitApprovalId': options.waitApprovalId,
                    'resModel': options.resModel,
                    'resId': options.resId,
                    'chatType': 'swap',
                }
            }
            return this._rpc({
                model: 'mail.channel',
                method: 'channel_get_and_minimize',
                args: [[partnerID]],
                kwargs: opt
            })
            .then(this._addChannel.bind(this));
        },
    })
});