/**
 *    Copyright (C) 2019 SuXueFeng
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU Affero General Public License as
 *    published by the Free Software Foundation, either version 3 of the
 *    License, or (at your option) any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Affero General Public License for more details.
 *
 *    You should have received a copy of the GNU Affero General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 **/

odoo.define('odoo.wage.archives.tree.button', function (require) {
    "use strict";

    let ListController = require('web.ListController');
    let ListView = require('web.ListView');
    let viewRegistry = require('web.view_registry');
    let KanbanController = require('web.KanbanController');
    let KanbanView = require('web.KanbanView');

    let OdooWageArchivesViewController = ListController.extend({
        buttons_template: 'OdooWageManageListView.wage_archives_buttons',
        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                let self = this;
                this.$buttons.on('click', '.batch_initialization_wage_archives_file', function () {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'wage.archives.transient',
                        target: 'new',
                        views: [[false, 'form']],
                        context: [],
                    },{
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

    let OdooWageArchivesManageListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: OdooWageArchivesViewController,
        }),
    });

    viewRegistry.add('wage_archives_js_class', OdooWageArchivesManageListView);


    let OdooWageArchivesKanbanController = KanbanController.extend({
        renderButtons: function ($node) {
            let $buttons = this._super.apply(this, arguments);
            let tree_model = this.modelName;
            if (tree_model == 'wage.archives') {
                let but = "<button type=\"button\" class=\"btn btn-secondary\">初始化档案</button>";
                let button2 = $(but).click(this.proxy('getWageArchivesTemBut'));
                this.$buttons.append(button2);
            }
            return $buttons;
        },
        getWageArchivesTemBut: function () {
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'wage.archives.transient',
                target: 'new',
                views: [[false, 'form']],
                context: [],
            },{
                on_reverse_breadcrumb: function () {
                    self.reload();
                },
                  on_close: function () {
                    self.reload();
                }
            });
        },
    });

    let OdooWageArchivesTemplateKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: OdooWageArchivesKanbanController,
        }),
    });

    viewRegistry.add('wage_archives_kanban_js_class', OdooWageArchivesTemplateKanbanView);

});