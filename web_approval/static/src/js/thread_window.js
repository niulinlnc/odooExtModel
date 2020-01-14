odoo.define('web_approval.mail.ThreadWindow', function (require) {
    var ThreadWindow = require('mail.ThreadWindow');

    ThreadWindow.include({
        // 沟通时，可以在所有用户中选择
        _startWithoutThread: function () {
            var self = this;
            var options = this.options; // xichun
            this.$el.addClass('o_thread_less');
            this.$('.o_thread_search_input input')
                .autocomplete({
                    source: function (request, response) {
                        self.call('mail_service', 'searchPartner', request.term, 10, options.approvalSwap)
                            .done(response);
                    },
                    select: function (event, ui) {
                        // remember partner ID so that we can replace this window
                        // with new DM chat window
                        var partnerID = ui.item.id;
                        self.directPartnerID = partnerID;
                        self.call('mail_service', 'openDMChatWindowFromBlankThreadWindow', partnerID, options);
                    }
                })
                .focus();
        },
    })
});