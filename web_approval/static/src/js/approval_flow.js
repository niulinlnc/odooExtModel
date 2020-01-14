odoo.define('web_approval.approvalInfo', function (require) {
    var Widget = require('web.Widget');

    return Widget.extend({
        template: "approval.Composer",
        events: {
            'click .btn-swap': '_onSwap',
            'click .btn-turn-to': '_onTurnTo',
            'click .btn-increase': '_onIncrease',
            'click .btn-approval': '_onApproval',
        },
        init: function (parent, record) {
            this._super(parent);
            var approvalData = record.approvalData;
            if(approvalData) {
                if (approvalData instanceof Array) {
                    approvalData = approvalData[0]
                }
                this.approvalInfo = approvalData.approvalInfo;
            }

        },
        _onSwap: function (e) {
            var btn = $(e.target);
            var options = {
                'waitApprovalId': btn.data('wait_approval_id'),
                'resModel': btn.data('res_model'),
                'resId': btn.data('res_id'),
                'approvalSwap': 1
            };
            this.call('mail_service', 'openBlankThreadWindow', options);
        },
        _onIncrease: function (e) {
            var btn = $(e.target);
            var self = this;
            this.do_action({
                name: '加签',
                type: 'ir.actions.act_window',
                // view_type: 'form',
                view_mode: 'form',
                res_model: 'approval.increase.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    wait_approval_id: btn.data('wait_approval_id'),
                    res_model: btn.data('res_model'),
                    res_id: btn.data('res_id'),
                    approval_supper: 1
                }
            },
                // 动作完成后回调，重新获取审批信息，并更新审批信
                {
                on_close: function (res) {
                    if(res !== 'special'){
                        self._update();
                    }
                }
            })
        },
        _onTurnTo: function (e) {
            var btn = $(e.target);
            var self = this;
            this.do_action({
                name: '代签',
                type: 'ir.actions.act_window',
                // view_type: 'form',
                view_mode: 'form',
                res_model: 'approval.turn.to.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    wait_approval_id: btn.data('wait_approval_id'),
                    res_model: btn.data('res_model'),
                    res_id: btn.data('res_id'),
                    approval_supper: 1
                }
            },
                // 动作完成后回调，重新获取审批信息，并更新审批信
                {
                on_close: function (res) {
                    if(res !== 'special'){
                        self._update();
                    }
                }
            })
        },
        _onApproval: function (e) {
            var btn = $(e.target);
            var self = this;
            this.do_action({
                name: '审批',
                type: 'ir.actions.act_window',
                // view_type: 'form',
                view_mode: 'form',
                res_model: 'approval.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    wait_approval_id: btn.data('wait_approval_id'),
                    res_model: btn.data('res_model'),
                    res_id: btn.data('res_id'),
                    approval_supper: 1
                }
            },
                // 动作完成后回调，重新获取审批信息，并更新审批信
                {
                on_close: function (res) {
                    if(res !== 'special'){
                        self._update();
                    }
                }
            })
        },
        _updateApprovalState: function (data) {
            var chatter = this.getParent();
            chatter.record.approvalData = data;
            this.trigger_up('update_header_button_state', data); // FormController更新HeaderButton状态
            chatter._onOpenApproval(); // 更新Chatter审批信息
        },
        // 重新获取审批信息，并重新render
        _update: function () {
            var self = this;
            var chatter = this.getParent();
            var controller = this.getParent().getParent().getParent(); // Form Controller
            controller.model._getApprovalInfo(chatter.record, function (data) {
                self._updateApprovalState(data)
            });


        },


    })
});