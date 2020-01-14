odoo.define('web_approval.Chatter', function (require) {
    var Chatter = require('mail.Chatter');
    var ChatterComposer = require('mail.composer.Chatter');
    var config = require('web.config');
    var approvalInfo = require('web_approval.approvalInfo');

    $.extend(Chatter.prototype.events, {
        'click .o_chatter_button_approval': '_onOpenApproval'
    });

    Chatter.include({
        // 点击'审批信息'
        _onOpenApproval: function () {
            if(this.$('.o_chatter_button_approval').hasClass('o_hidden')){
                return
            }
            var self = this;
            var oldApprovalInfo = this._approvalInfo;
            this._approvalInfo = new approvalInfo(this, this.record);
            this._approvalInfo.insertAfter(this.$('.o_chatter_topbar')).then(function () {
                if(self._composer){
                    self._composer.destroy()
                }
                if(oldApprovalInfo){
                    oldApprovalInfo.destroy();
                }
                self._renderNavigationButton(true);
            });
        },
        // @override
        _openComposer: function (options) {
            var self = this;
            var oldComposer = this._composer;
            // create the new composer
            this._composer = new ChatterComposer(this, this.record.model, options.suggested_partners || [], {
                commandsEnabled: false,
                context: this.context,
                inputMinHeight: 50,
                isLog: options && options.isLog,
                recordName: this.recordName,
                defaultBody: oldComposer && oldComposer.$input && oldComposer.$input.val(),
                defaultMentionSelections: oldComposer && oldComposer.getMentionListenerSelections(),
            });
            this._composer.on('input_focused', this, function () {
                this._composer.mentionSetPrefetchedPartners(this._mentionSuggestions || []);
            });
            this._composer.insertAfter(this.$('.o_chatter_topbar')).then(function () {
                // destroy existing composer
                if (oldComposer) {
                    oldComposer.destroy();
                }
                if(self._approvalInfo){
                    self._approvalInfo.destroy()
                }
                if (!config.device.isMobile) {
                    self._composer.focus();
                }
                self._composer.on('post_message', self, function (messageData) {
                    self._discardOnReload(messageData).then(function () {
                        self._disableComposer();
                        self.fields.thread.postMessage(messageData).then(function () {
                            self._closeComposer(true);
                            if (self._reloadAfterPost(messageData)) {
                                self.trigger_up('reload');
                            } else if (messageData.attachment_ids.length) {
                                self.trigger_up('reload', {fieldNames: ['message_attachment_count']});
                            }
                        }).fail(function () {
                            self._enableComposer();
                        });
                    });
                });
                self._composer.on('need_refresh', self, self.trigger_up.bind(self, 'reload'));
                self._composer.on('close_composer', null, self._closeComposer.bind(self, true));

                self._renderNavigationButton();
            });

        },
        _renderNavigationButton: function (options) {
            this.$el.addClass('o_chatter_composer_active');
            this.$('.o_chatter_button_new_message, .o_chatter_button_log_note, .o_chatter_button_approval').removeClass('o_active');
            if(options){
                this.$('.o_chatter_button_approval').addClass('o_active')
            }
            else{
                this.$('.o_chatter_button_new_message').toggleClass('o_active', !this._composer.options.isLog);
                this.$('.o_chatter_button_log_note').toggleClass('o_active', this._composer.options.isLog);
            }
        },
        // 当Chatter只有"审批信息"时，默认显示审批内容
        _render: function (def) {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._showApproval()
            })
        },
        _showApproval: function () {
            var self = this;
            var def = $.Deferred();
            if(this._approvalInfo){
                this._approvalInfo.destroy();
            }
            this.$('.o_chatter_button_approval').removeClass('o_active');
            var approvalData = this.record.approvalData;
            if(approvalData){
                if(approvalData instanceof Array){
                    approvalData = approvalData[0]
                }
                var buttonState = approvalData.buttonState;

                this.$('.o_chatter_button_approval').toggleClass('o_hidden', !buttonState.chatter_approval);
            }

            if (!self._isCreateMode && self._$topbar.children().length === 2) {
                $.when(self._onOpenApproval()).then(function () {
                   def.resolve()
                })
            }
            else {
                def.resolve()
            }

            return def
        },
        // // @override
        // // 重新render审批信息 TODO
        // update: function (record, fieldNames) {
        //     this._closeApprovalComposer();
        //     return this._super.apply(this, arguments);
        //
        // },
        // _closeApprovalComposer: function () {
        //
        // }
    })

});
