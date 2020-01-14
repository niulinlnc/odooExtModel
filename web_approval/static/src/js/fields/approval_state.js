odoo.define('web.approval_state_fields', function (require) {
    // tree视图中显示审批状态Html内容
    var AbstractField = require('web.AbstractField');
    var registry = require('web.field_registry');

    var FieldApprovalState = AbstractField.extend({
        supportedFieldTypes: ['char'],

        isSet: function () {
            return true;
        },
        _render: function () {
            this.value && this.$el.html(this.value);
        }
    });

    registry.add('approval_state', FieldApprovalState)
});

