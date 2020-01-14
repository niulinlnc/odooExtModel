odoo.define('web_approval.mail.Manager', function (require) {
    var mailManager = require('mail.Manager');
    var session = require('web.session');
    var mailUtils = require('mail.utils');

    mailManager.include({
        _redirectToDocument: function (resModel, resID, viewID) {
            this.do_action({
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: resModel,
                views: [[viewID || false, 'form']],
                res_id: resID,
                context: {
                    approval_supper: 1
                }
            });
        },
        searchPartner: function (searchVal, limit, scope) {
            var def = $.Deferred();
            var partners = this._searchPartnerPrefetch(searchVal, limit, scope);

            if (!partners.length) {
                // def = this._searchPartnerFetch(searchVal, limit); // xichun, 不从服务器得到数据
                def = $.when([]);
            } else {
                def = $.when(partners);
            }
            return def.then(function (partners) {
                var suggestions = _.map(partners, function (partner) {
                    return {
                        id: partner.id,
                        value: partner.name,
                        label: partner.name
                    };
                });
                return _.sortBy(suggestions, 'label');
            });
        },
        _searchPartnerPrefetch: function (searchVal, limit, scope) {
            var values = [];
            var company_id = session.company_id;
            scope = !!scope;
            var searchRegexp = new RegExp(_.str.escapeRegExp(mailUtils.unaccent(searchVal)), 'i');
            _.each(this._mentionPartnerSuggestions, function (partners) {
                if (values.length < limit) {
                    values = values.concat(_.filter(partners, function (partner) {
                        if(scope){
                            return (session.partner_id !== partner.id) && searchRegexp.test(partner.name);
                        }
                        else{
                            return (session.partner_id !== partner.id) && searchRegexp.test(partner.name) && partner.cid === company_id;
                        }

                    })).splice(0, limit);
                }
            });
            return values;
        },
        // _addChannel: function (data, options) {
        //
        // }
    });

});