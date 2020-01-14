odoo.define('web_approval.mail.model.DMChat', function (require) {
    var DMChat = require('mail.model.DMChat');
    DMChat.include({
        init: function (params) {
            this._super.apply(this, arguments);
            if(this._serverType === 'swap'){
                this._type = 'swap';
                this._name = params.data.name
            }

        },
    })

});