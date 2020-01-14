odoo.define('web_approval.FormRenderer', function (require) {
    var formRenderer = require('web.FormRenderer');
    var core = require('web.core');
    $.extend(formRenderer.prototype.custom_events, {
        update_header_button_state: '_updateHeaderButtonState',
    });
    formRenderer.include({
        // @override
        _renderTagHeader: function (node) {
            var $statusbar = this._super.apply(this, arguments);
            this._renderApprovalButton($statusbar);
            return $statusbar;
        },
        // 更新Header审批相关按钮状态
        _renderApprovalButton: function ($statusbar) {
            var approvalData = this.state.approvalData;
            if(approvalData){
                if(approvalData instanceof Array){
                    approvalData = approvalData[0]
                }
                var buttonState = approvalData.buttonState;
                $statusbar.find('.commit_approval').toggleClass('o_hidden', !buttonState.commit_approval);
                $statusbar.find('.pause_approval').toggleClass('o_hidden', !buttonState.pause_approval);
                $statusbar.find('.resume_approval').toggleClass('o_hidden', !buttonState.resume_approval);
                $statusbar.find('.cancel_approval').toggleClass('o_hidden', !buttonState.cancel_approval);
                $statusbar.find('.btn-download-sign-doc').toggleClass('o_hidden', !buttonState.download_doc); // 下载签名单据
                // $statusbar.find('.btn-do-swap').toggleClass('o_hidden', !buttonState.approval_swap);

                // this.$('.o_chatter_button_approval').toggleClass('o_hidden', !buttonState.chatter_approval);
            }
        },
        _updateHeaderButtonState: function (odooEvent) {
            var approvalData = odooEvent.data;
            if(approvalData){
                var buttonState = approvalData[0].buttonState;
                this.$('.commit_approval').toggleClass('o_hidden', !buttonState.commit_approval);
                this.$('.pause_approval').toggleClass('o_hidden', !buttonState.pause_approval);
                this.$('.resume_approval').toggleClass('o_hidden', !buttonState.resume_approval);
                this.$('.cancel_approval').toggleClass('o_hidden', !buttonState.cancel_approval);
                this.$('.btn-download-sign-doc').toggleClass('o_hidden', !buttonState.download_doc); // 下载签名单据
                // this.$('.btn-do-swap').toggleClass('o_hidden', !buttonState.approval_swap);

                // this.$('.o_chatter_button_approval').toggleClass('o_hidden', !buttonState.chatter_approval);
            }
        },
        _addOnClickAction: function ($el, node) {
            var self = this;
            if($el.hasClass('btn-diagram')){
                $el.click(function () {
                    self.trigger_up('btn_diagram_clicked', {
                        attrs: node.attrs,
                        record: self.state,
                    });
                });
            }
            // // 下载签名单据
            // else if($el.hasClass('btn-download-sign-doc')){
            //     $el.click(function () {
            //         self.trigger_up('download_sign_clicked', {
            //             attrs: node.attrs,
            //             record: self.state,
            //         });
            //     });
            // }
            else{
                this._super($el, node)
            }
        },
    })

});