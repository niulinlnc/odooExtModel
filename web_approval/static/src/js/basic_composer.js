odoo.define('wab_approval.mail.composer.Basic', function (require) {
    var composer = require('mail.composer.Basic');
    composer.include({
        // TODO email_from=false没有效果
        _preprocessMessage: function () {
            var self = this;
            return $.when(this._super()).then(function (message) {
                if(self.options.thread != null){
                    if(self.options.thread.getType() === 'swap'){
                        message.email_from = false;
                    }
                }
                return $.when(message)
            })
        }
    });
});
