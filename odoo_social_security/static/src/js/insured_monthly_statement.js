odoo.define('insured.monthly.statement.tree.button', function (require) {
    "use strict";

    let ListController = require('web.ListController');
    let ListView = require('web.ListView');
    let viewRegistry = require('web.view_registry');

    let InsuredMonthlyStatementController = ListController.extend({
        buttons_template: 'ListView.insured_monthly_statement_buttons',
        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                var self = this;
                this.$buttons.on('click', '.insured_monthly_statement_class', function () {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'compute.insured.monthly.statement',
                        target: 'new',
                        views: [[false, 'form']],
                        context: [],
                    }, {
                        on_reverse_breadcrumb: function () {
                            self.reload();
                        },
                        on_close: function () {
                            self.reload();
                        }
                    });
                });
            }
        }
    });

    let InsuredMonthlyStatementView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: InsuredMonthlyStatementController,
        }),
    });

    viewRegistry.add('insured_monthly_statement_tree_class', InsuredMonthlyStatementView);

});