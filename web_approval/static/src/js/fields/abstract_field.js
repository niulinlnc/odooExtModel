odoo.define('web_approval.AbstractField', function (require) {
    var AbstractField = require('web.AbstractField');
    AbstractField.include({
        // @override
        // 字段change时，把action的context传进去
        _setValue: function (value, options) {
            if (this.lastSetValue === value || (this.value === false && value === '')) {
                return $.when();
            }
            this.lastSetValue = value;
            try {
                value = this._parseValue(value);
                this._isValid = true;
            } catch (e) {
                this._isValid = false;
                this.trigger_up('set_dirty', {dataPointID: this.dataPointID});
                return $.Deferred().reject();
            }
            if (!(options && options.forceChange) && this._isSameValue(value)) {
                return $.when();
            }
            var def = $.Deferred();
            var changes = {};
            changes[this.name] = value;
            this.trigger_up('field_changed', {
                dataPointID: this.dataPointID,
                changes: changes,
                viewType: this.viewType,
                doNotSetDirty: options && options.doNotSetDirty,
                notifyChange: !options || options.notifyChange !== false,
                allowWarning: options && options.allowWarning,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
                context: this.record.getContext(this.recordParams), // xichun
            });
            return def;
        }
    })
});

