odoo.define('web_approval.mail.Discuss', function (require) {
    var Discuss = require('mail.Discuss');

    Discuss.include({
        _updateControlPanelButtons: function (thread) {
            this._super(thread);
            if(thread._type === 'swap'){
                this.$buttons
                    .find('.o_mail_discuss_button_invite, .o_mail_discuss_button_settings')
                    .removeClass('d-none d-md-inline-block')
                    .addClass('d-none');
            }
        }
    });

});