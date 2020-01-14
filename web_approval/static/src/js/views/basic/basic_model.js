odoo.define('web_approval.BasicModel', function (require) {
    var BasicModel = require('web.BasicModel');
    BasicModel.include({
        // @override
        _fetchRecord: function (record, options) {
            var self = this;
            return this._super.apply(this, arguments).then(function (record) {
                return self._getApprovalInfo(record, function (result) {
                    record.approval_info = result;
                    return record
                })
            })
        },

        // 获取审批信息
        _getApprovalInfo: function (record, fun) {
            return this._rpc({
                model: record.model,
                method: 'get_approval_info',
                args: [record.res_id, []],
                // context: {
                //     approval_supper: 1
                // }
            })
            .then(fun)
        },
        // @override
        // 当返回单条记录时，把审批信息返回回去
        get: function (id, options) {
            var result = this._super.apply(this, arguments);
            if (!(id in this.localData)) {
                return result;
            }
            var element = this.localData[id];
            if (element.type === 'record') {
                result.approvalData = element.approval_info
            }

            return result;
        },

        // @override
        // 字段change时，把action的context传进去
        _applyChange: function (recordID, changes, options) {
            var self = this;
            var record = this.localData[recordID];
            var field;
            var defs = [];
            options = options || {};
            record._changes = record._changes || {};
            if (!options.doNotSetDirty) {
                record._isDirty = true;
            }
            var initialData = {};
            this._visitChildren(record, function (elem) {
                initialData[elem.id] = $.extend(true, {}, _.pick(elem, 'data', '_changes'));
            });

            // apply changes to local data
            for (var fieldName in changes) {
                field = record.fields[fieldName];
                if (field.type === 'one2many' || field.type === 'many2many') {
                    // defs.push(this._applyX2ManyChange(record, fieldName, changes[fieldName], options.viewType, options.allowWarning));
                    defs.push(this._applyX2ManyChange(record, fieldName, changes[fieldName], options.viewType, options.allowWarning, options.context)); // xichun
                } else if (field.type === 'many2one' || field.type === 'reference') {
                    defs.push(this._applyX2OneChange(record, fieldName, changes[fieldName]));
                } else {
                    record._changes[fieldName] = changes[fieldName];
                }
            }

            if (options.notifyChange === false) {
                return $.Deferred().resolve(_.keys(changes));
            }

            return $.when.apply($, defs).then(function () {
                var onChangeFields = []; // the fields that have changed and that have an on_change
                for (var fieldName in changes) {
                    field = record.fields[fieldName];
                    if (field.onChange) {
                        var isX2Many = field.type === 'one2many' || field.type === 'many2many';
                        if (!isX2Many || (self._isX2ManyValid(record._changes[fieldName] || record.data[fieldName]))) {
                            onChangeFields.push(fieldName);
                        }
                    }
                }
                var onchangeDef = $.Deferred();
                if (onChangeFields.length) {
                    self._performOnChange(record, onChangeFields, options.viewType)
                        .then(function (result) {
                            delete record._warning;
                            onchangeDef.resolve(_.keys(changes).concat(Object.keys(result && result.value || {})));
                        }).fail(function () {
                            self._visitChildren(record, function (elem) {
                                _.extend(elem, initialData[elem.id]);
                            });
                            onchangeDef.resolve({});
                        });
                } else {
                    onchangeDef = $.Deferred().resolve(_.keys(changes));
                }
                return onchangeDef.then(function (fieldNames) {
                    _.each(fieldNames, function (name) {
                        if (record._changes && record._changes[name] === record.data[name]) {
                            delete record._changes[name];
                            record._isDirty = !_.isEmpty(record._changes);
                        }
                    });
                    return self._fetchSpecialData(record).then(function (fieldNames2) {
                        // Return the names of the fields that changed (onchange or
                        // associated special data change)
                        return _.union(fieldNames, fieldNames2);
                    });
                });
            });
        },
        // @override
        _applyX2ManyChange: function (record, fieldName, command, viewType, allowWarning, context) {
            if (command.operation === 'TRIGGER_ONCHANGE') {
                // the purpose of this operation is to trigger an onchange RPC, so
                // there is no need to apply any change on the record (the changes
                // have probably been already applied and saved, usecase: many2many
                // edition in a dialog)
                return $.when();
            }

            var self = this;
            var localID = (record._changes && record._changes[fieldName]) || record.data[fieldName];
            var list = this.localData[localID];
            var field = record.fields[fieldName];
            var fieldInfo = record.fieldsInfo[viewType || record.viewType][fieldName];
            var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
            var def, rec;
            var defs = [];
            list._changes = list._changes || [];

            switch (command.operation) {
                case 'ADD':
                    // for now, we are in the context of a one2many field
                    // the command should look like this:
                    // { operation: 'ADD', id: localID }
                    // The corresponding record may contain value for fields that
                    // are unknown in the list (e.g. fields that are in the
                    // subrecord form view but not in the kanban or list view), so
                    // to ensure that onchanges are correctly handled, we extend the
                    // list's fields with those in the created record
                    var newRecord = this.localData[command.id];
                    _.defaults(list.fields, newRecord.fields);
                    _.defaults(list.fieldsInfo, newRecord.fieldsInfo);
                    newRecord.fields = list.fields;
                    newRecord.fieldsInfo = list.fieldsInfo;
                    newRecord.viewType = list.viewType;
                    list._cache[newRecord.res_id] = newRecord.id;
                    list._changes.push(command);
                    break;
                case 'ADD_M2M':
                    // force to use link command instead of create command
                    list._forceM2MLink = true;
                    // handle multiple add: command[2] may be a dict of values (1
                    // record added) or an array of dict of values
                    var data = _.isArray(command.ids) ? command.ids : [command.ids];

                    // Ensure the local data repository (list) boundaries can handle incoming records (data)
                    if (data.length + list.res_ids.length > list.limit) {
                        list.limit = data.length + list.res_ids.length;
                    }

                    var list_records = {};
                    _.each(data, function (d) {
                        rec = self._makeDataPoint({
                            context: record.context,
                            modelName: field.relation,
                            fields: view ? view.fields : fieldInfo.relatedFields,
                            fieldsInfo: view ? view.fieldsInfo : fieldInfo.fieldsInfo,
                            res_id: d.id,
                            data: d,
                            viewType: view ? view.type : fieldInfo.viewType,
                            parentID: list.id,
                        });
                        list_records[d.id] = rec;
                        list._cache[rec.res_id] = rec.id;
                        list._changes.push({operation: 'ADD', id: rec.id});
                    });
                    // read list's records as we only have their ids and optionally their display_name
                    // (we can't use function readUngroupedList because those records are only in the
                    // _changes so this is a very specific case)
                    // this could be optimized by registering the fetched records in the list's _cache
                    // so that if a record is removed and then re-added, it won't be fetched twice
                    var fieldNames = list.getFieldNames();
                    if (fieldNames.length) {
                        def = this._rpc({
                            model: list.model,
                            method: 'read',
                            args: [_.pluck(data, 'id'), fieldNames],
                            // context: record.context,
                            context: $.extend(context || {}, record.context) // xichun
                        }).then(function (records) {
                            _.each(records, function (record) {
                                list_records[record.id].data = record;
                                self._parseServerData(fieldNames, list, record);
                            });
                            return $.when(
                                self._fetchX2ManysBatched(list),
                                self._fetchReferencesBatched(list)
                            );
                        });
                        defs.push(def);
                    }
                    break;
                case 'CREATE':
                    var options = {
                        context: command.context,
                        position: command.position,
                        allowWarning: allowWarning
                    };
                    def = this._addX2ManyDefaultRecord(list, options).then(function (ids) {
                        _.each(ids, function(id){
                            if (command.position === 'bottom' && list.orderedResIDs && list.orderedResIDs.length >= list.limit) {
                                list.tempLimitIncrement = (list.tempLimitIncrement || 0) + 1;
                                list.limit += 1;
                            }
                            // FIXME: hack for lunch widget, which does useless default_get and onchange
                            if (command.data) {
                                return self._applyChange(id, command.data);
                            }
                        });
                    });
                    defs.push(def);
                    break;
                case 'UPDATE':
                    list._changes.push({operation: 'UPDATE', id: command.id});
                    if (command.data) {
                        defs.push(this._applyChange(command.id, command.data));
                    }
                    break;
                case 'FORGET':
                    // Unlink the record of list.
                    list._forceM2MUnlink = true;
                case 'DELETE':
                    // filter out existing operations involving the current
                    // dataPoint, and add a 'DELETE' or 'FORGET' operation only if there is
                    // no 'ADD' operation for that dataPoint, as it would mean
                    // that the record wasn't in the relation yet
                    var idsToRemove = command.ids;
                    list._changes = _.reject(list._changes, function (change, index) {
                        var idInCommands = _.contains(command.ids, change.id);
                        if (idInCommands && change.operation === 'ADD') {
                            idsToRemove = _.without(idsToRemove, change.id);
                        }
                        return idInCommands;
                    });
                    _.each(idsToRemove, function (id) {
                        var operation = list._forceM2MUnlink ? 'FORGET': 'DELETE';
                        list._changes.push({operation: operation, id: id});
                    });
                    break;
                case 'REPLACE_WITH':
                    // this is certainly not optimal... and not sure that it is
                    // correct if some ids are added and some other are removed
                    list._changes = [];
                    var newIds = _.difference(command.ids, list.res_ids);
                    var removedIds = _.difference(list.res_ids, command.ids);
                    var addDef, removedDef, values;
                    if (newIds.length) {
                        values = _.map(newIds, function (id) {
                            return {id: id};
                        });
                        addDef = this._applyX2ManyChange(record, fieldName, {
                            operation: 'ADD_M2M',
                            ids: values
                        });
                    }
                    if (removedIds.length) {
                        var listData = _.map(list.data, function (localId) {
                            return self.localData[localId];
                        });
                        removedDef = this._applyX2ManyChange(record, fieldName, {
                            operation: 'DELETE',
                            ids: _.map(removedIds, function (resID) {
                                if (resID in list._cache) {
                                    return list._cache[resID];
                                }
                                return _.findWhere(listData, {res_id: resID}).id;
                            }),
                        });
                    }
                    return $.when(addDef, removedDef);
            }

            return $.when.apply($, defs).then(function () {
                // ensure to fetch up to 'limit' records (may be useful if records of
                // the current page have been removed)
                return self._readUngroupedList(list).then(function () {
                    return self._fetchX2ManysBatched(list);
                });
            });
        },

        //获取流程图数据
        getDiagramData: function(recordID) {
            var record = this.localData[recordID];
            return this._rpc({
                model: record.model,
                method: 'get_diagram_data',
                args: [record.data.id]
            })
        },

        _makeDefaultRecord: function (modelName, params) {
            var self = this;

            var targetView = params.viewType;
            var fields = params.fields;
            var fieldsInfo = params.fieldsInfo;
            var fieldNames = Object.keys(fieldsInfo[targetView]);
            var fields_key = _.without(fieldNames, '__last_update');

            // Fields that are present in the originating view, that need to be initialized
            // Hence preventing their value to crash when getting back to the originating view
            var parentRecord = self.localData[params.parentID];
            if (parentRecord) {
                var originView = parentRecord.viewType;
                fieldNames = _.union(fieldNames, Object.keys(parentRecord.fieldsInfo[originView]));
                fieldsInfo[targetView] = _.defaults({}, fieldsInfo[targetView], parentRecord.fieldsInfo[originView]);
                fields = _.defaults({}, fields, parentRecord.fields);
            }

            return this._rpc({
                    model: modelName,
                    method: 'default_get',
                    args: [fields_key],
                    context: params.context,
                })
                .then(function (result) {
                    var record = self._makeDataPoint({
                        modelName: modelName,
                        fields: fields,
                        fieldsInfo: fieldsInfo,
                        context: params.context,
                        parentID: params.parentID,
                        res_ids: params.res_ids,
                        viewType: targetView,
                    });

                    // We want to overwrite the default value of the handle field (if any),
                    // in order for new lines to be added at the correct position.
                    // -> This is a rare case where the defaul_get from the server
                    //    will be ignored by the view for a certain field (usually "sequence").

                    var overrideDefaultFields = self._computeOverrideDefaultFields(
                        params.parentID,
                        params.position
                    );

                    // bug修复
                    if (Object.keys(overrideDefaultFields).length > 0) {
                        result[overrideDefaultFields.field] = overrideDefaultFields.value;
                    }

                    return self.applyDefaultValues(record.id, result, {fieldNames: fieldNames})
                        .then(function () {
                            var def = $.Deferred();
                            self._performOnChange(record, fields_key).always(function () {
                                if (record._warning) {
                                    if (params.allowWarning) {
                                        delete record._warning;
                                    } else {
                                        def.reject();
                                    }
                                }
                                def.resolve();
                            });
                            return def;
                        })
                        .then(function () {
                            return self._fetchRelationalData(record);
                        })
                        .then(function () {
                            return self._postprocess(record);
                        })
                        .then(function () {
                            // save initial changes, so they can be restored later,
                            // if we need to discard.
                            self.save(record.id, {savePoint: true});

                            return record.id;
                        });
                });
        },
    })
});

