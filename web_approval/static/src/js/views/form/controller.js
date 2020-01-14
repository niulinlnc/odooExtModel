odoo.define('web_approval.FormController', function (require) {
    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');
    var session = require('web.session');

    $.extend(FormController.prototype.custom_events, {
        btn_diagram_clicked: '_onButtonDiagramClicked',
        // btn_swap_clicked: '_onButtonSwapClicked',
    });

    FormController.include({
        // @override
        // Show/Hide Diagram
        _onButtonDiagramClicked: function (event) {
            event.stopPropagation();

            // 创建时不显示图
            var isNew = this.model.isNew(this.handle);
            if(isNew)
                return;

            this._disableButtons();

            if(!this.diagramElement){
                this.diagramElement = document.getElementById("diagramContainer");
                this._instanceDiagram();
            }

            var display = this.diagramElement.style.display;
            if(display === 'block'){
                $(this.diagramElement).hide();
                this._enableButtons();
            }
            else{
                var self = this;
                this.model.getDiagramData(this.handle)
                    .then(function (data) {
                        self._enableButtons();
                        if (data.nodes.length === 2) {
                            self.do_warn('Warning', '请定义审批流程节点！');
                        }
                        else {
                            self._renderDiagram(data);
                        }
                    });
            }
        },
        // @override
        // Hide Diagram
        _update: function () {
            if(this.diagramElement){
                $(this.diagramElement).empty().hide();
                delete this.diagramElement;
                delete this.diagram;
            }
            return  this._super.apply(this, arguments)
        },
        // @override
        // Delete diagramElement and diagram
        destroy: function () {
            if(this.diagramElement){
                delete this.diagramElement;
                delete this.diagram;
            }
            return this._super.apply(this, arguments)
        },

        _instanceDiagram: function () {
            if(this.diagram)
                return;

            var self = this;

            this.diagram = this._diagramDefine();
            this.diagram.addDiagramListener("Modified", this._diagramModified);
            this.diagram.nodeTemplate = this._diagramDefaultNodeTemplate();
            // if(session.is_approval_config){
            //     this.diagram.nodeTemplate.contextMenu = this._diagramContextMenu('node');
            //     this.diagram.linkTemplate.contextMenu = this._diagramContextMenu('link');
            // }

            this.diagram.nodeTemplateMap.add("Start", this._diagramStartNodeTemplate());
            this.diagram.nodeTemplateMap.add("End", this._diagramEndNodeTemplate());
            this.diagram.linkTemplate = this._diagramLinkTemplate();

            // 图连接时
            this.diagram.addDiagramListener("LinkDrawn", this._addActionWizard.bind(this));
            // 删除对象时
            this.diagram.addDiagramListener("SelectionDeleting", this._selectionDeleting.bind(this));
            this.diagram.addDiagramListener("LinkRelinked", function (e) {
                var link = e.subject;
                if (link.toNode.category === "Recycle") self.diagram.remove(link);
                self._lowLight();
            });

        },
        // 删除元素时
        _selectionDeleting: function (e) {
            var self = this;
            var part = e.subject.first();
            this.diagram.startTransaction("clear boss");
            if(!session.is_approval_config){
                e.cancel = true;
                this.diagram.rollbackTransaction("clear boss");
            }
            if (part instanceof go.Node) {
                e.cancel = true;
                this.diagram.rollbackTransaction("clear boss");
            } else if (part instanceof go.Link) {
                e.cancel = true;
                this.diagram.rollbackTransaction("clear boss");
                this._deleteLink(part);
            }
            else {
                this.diagram.commitTransaction("clear boss");
            }
        },
        _deleteLink: function (part) {
            var self = this;
            var message = '确认删除选择的动作吗？';
            var options = {
                title: '删除动作',
                size: 'medium',
                buttons: [
                    {
                        text: '确认', close: true, classes: 'btn-primary', click: function () {
                            self.diagram.model.removeLinkData(part.data);
                        }
                    },
                    {
                        text: '取消', close: true, click: function () {
                        }
                    }
                ],
            };
            Dialog.confirm(self, message, options);
        },
        // 添加动作
        _addActionWizard: function (e) {
            var recordID = this.model.get(this.handle, {raw: true}).res_id;
            var link = e.subject;
            this.diagram.remove(link);
            if(!session.is_approval_config)
                return;

            var self = this;
            this.do_action({
                    name: '添加动作',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    res_model: 'add.node.action.wizard',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                        from: parseInt(link.data.from),
                        to: parseInt(link.data.to),
                        flow_id: recordID
                    }
                },
                {
                    on_close: function (res) {
                        if (res !== 'special') {
                            self.diagram.add(link)
                        }
                    }
                });
        },
        // 图修改监听
        _diagramModified: function (e) {
            // TODO
        },
        // 上下文菜单
        _diagramContextMenu: function (type) {
            return odoo.$$(go.Adornment, "Vertical",
                odoo.$$("ContextMenuButton",
                    odoo.$$(go.TextBlock, "编辑"),
                    {
                        click: function (e, obj) {
                            e.diagram.commandHandler.editTextBlock();
                        }
                    },
                    new go.Binding("visible", "", function (o) {
                        return true;
                        // return o.diagram && o.diagram.commandHandler.canEditTextBlock();
                    }).ofObject()
                ),
                // add one for Editing...
                odoo.$$("ContextMenuButton",
                    odoo.$$(go.TextBlock, "删除"),
                    {
                        click: function (e, obj) {
                            e.diagram.commandHandler.deleteSelection();
                        }
                    },
                    new go.Binding("visible", "", function (o) {
                        return o.diagram && o.diagram.commandHandler.canDeleteSelection();
                    }).ofObject()
                )
            );
        },
        // 图元入链接
        _diagramNodeInputPort: function () {
            return odoo.$$(go.Panel, "Auto",
                {
                    alignment: go.Spot.Left,
                    portId: "to",
                    toLinkable: true
                },
                odoo.$$(go.Shape, "Circle",
                    {
                        width: 8,
                        height: 8,
                        fill: "white",
                        stroke: "gray"
                    }
                ),
                odoo.$$(go.Shape, "Circle",
                    {
                        width: 4,
                        height: 4,
                        fill: "dodgerblue",
                        stroke: null
                    }
                )
            )
        },
        // 图元出链接
        _diagramNodeOutputPort: function () {
            return odoo.$$(go.Panel, "Auto",
                {
                    alignment: go.Spot.Right,
                    portId: "from",
                    fromLinkable: true,
                    cursor: "pointer",
                    // click: this._addNodeAndLink
                },
                odoo.$$(go.Shape, "Circle",
                    {
                        width: 16,
                        height: 16,
                        fill: "white",
                        stroke: "dodgerblue",
                        strokeWidth: 2
                    }
                ),
                odoo.$$(go.Shape, "PlusLine",
                    {
                        width: 8,
                        height: 8,
                        fill: null,
                        stroke: "dodgerblue",
                        strokeWidth: 2
                    }
                )
            )
        },        
        // 图连接模板
        _diagramLinkTemplate: function () {
            return odoo.$$(go.Link,
                {
                    selectionAdorned: false,
                    fromPortId: "from",
                    toPortId: "to",
                    relinkableTo: false
                },
                odoo.$$(go.Shape,
                    {
                        stroke: "gray",
                        strokeWidth: 2
                    },
                    {
                        mouseEnter: function (e, obj) {
                            obj.strokeWidth = 4;
                            obj.stroke = "dodgerblue";
                        },
                        mouseLeave: function (e, obj) {
                            obj.strokeWidth = 2;
                            obj.stroke = "gray";
                        }
                    }
                ),
                odoo.$$(go.Shape, {toArrow: "OpenTriangle", fill: 'gray'}),
                odoo.$$(go.Panel, "Auto",
                    {
                        _isLinkLabel: true,
                        // toolTip: myToolTip,
                        mouseEnter: this._diagramLinkLabelMouseEnter,
                        mouseLeave: this._diagramLinkLabelMouseLeave
                    },  // marks this Panel as being a draggable label
                    odoo.$$(go.Shape, {fill: "white"}),
                    // odoo.$$(go.TextBlock, "条件", {'font': '9px sans-serif'}, new go.Binding("text", "text")),
                    odoo.$$(go.TextBlock, "条件", {'font': '9px sans-serif'}),
                    // remember any modified segment properties in the link data object
                    // new go.Binding("segmentIndex").makeTwoWay(),
                    // new go.Binding("segmentFraction").makeTwoWay(),
                    new go.Binding("visible", "", function (o) {
                        return !!o.data.condition;
                    }).ofObject()
                )
            );
        },
        _diagramLinkLabelMouseEnter: function (e, obj) {
            var mousePt = e.viewPoint;
            var box = document.getElementById("infoBoxHolder");
            box.style.display = 'block';
            box.innerHTML = '';

            var infobox = document.createElement("div");
            infobox.id = "infoBox";
            box.appendChild(infobox);

            infobox.textContent = obj.part.data.condition;

            box.style.left = mousePt.x + 30 + "px";
            box.style.top = mousePt.y + 20 + "px";
        },
        _diagramLinkLabelMouseLeave: function (e, obj) {
            document.getElementById('infoBoxHolder').style.display = 'none'
        },        
        // 图结束节点模板
        _diagramEndNodeTemplate: function () {
            return odoo.$$(go.Node, "Spot",
                {
                    selectionAdorned: false,
                    textEditable: false,
                    locationObjectName: "BODY"
                },
                new go.Binding("location", "loc", go.Point.parse).makeTwoWay(go.Point.stringify),
                // the main body consists of a Rectangle surrounding the text
                odoo.$$(go.Panel, "Auto",
                    {name: "BODY"},
                    odoo.$$(go.Shape, "Ellipse",
                        {
                            fill: graygrad,
                            stroke: "gray",
                            // minSize: new go.Size(120, 21)
                        },
                        new go.Binding("fill", "isSelected", function (s) {
                            return s ? "dodgerblue" : graygrad;
                        }).ofObject()
                    ),
                    odoo.$$(go.TextBlock,
                        {
                            stroke: "black",
                            font: "12px sans-serif",
                            editable: false,
                            margin: new go.Margin(3, 3, 3, 3),
                            alignment: go.Spot.Left
                        },
                        new go.Binding("text", "text")
                    )
                ),
                // input port
                this._diagramNodeInputPort()
            )
        },
        // 图开始节点模板
        _diagramStartNodeTemplate: function () {
            return odoo.$$(go.Node, "Spot",
                {
                    selectionAdorned: false,
                    textEditable: true,
                    locationObjectName: "BODY"
                },
                new go.Binding("location", "loc", go.Point.parse).makeTwoWay(go.Point.stringify),
                // the main body consists of a Rectangle surrounding the text
                odoo.$$(go.Panel, "Auto",
                    {name: "BODY"},
                    odoo.$$(go.Shape, "Ellipse",
                        {
                            fill: graygrad,
                            stroke: "gray",
                            // minSize: new go.Size(120, 21)
                        },
                        new go.Binding("fill", "isSelected", function (s) {
                            return s ? "dodgerblue" : graygrad;
                        }).ofObject()
                    ),
                    odoo.$$(go.TextBlock,
                        {
                            stroke: "black",
                            // font: "12px sans-serif",
                            editable: false,
                            margin: new go.Margin(3, 3 + 4, 3, 3),
                            alignment: go.Spot.Center
                        },
                        new go.Binding("text", "text")
                    )
                ),
                // output port
                this._diagramNodeOutputPort()
            )
        },
        // 图默认节点模板
        _diagramDefaultNodeTemplate: function () {
            var node_body = function () {
                return odoo.$$(go.Panel, "Auto",
                    {name: "BODY"},
                    odoo.$$(go.Shape,
                        // "Rectangle",
                        "RoundedRectangle",
                        {
                            fill: graygrad,
                            stroke: "gray",
                            // minSize: new go.Size(120, 21)
                        },
                        new go.Binding("fill", "isSelected", function (s) {
                            return s ? "dodgerblue" : graygrad;
                        }).ofObject()
                    ),
                    odoo.$$(go.TextBlock,
                        {
                            stroke: "black",
                            // font: "12px sans-serif",
                            editable: false,
                            margin: new go.Margin(3, 3 + 11, 3, 3 + 4),
                            alignment: go.Spot.Left
                        },
                        new go.Binding("text").makeTwoWay()
                    )
                )
            };
            return odoo.$$(go.Node, "Spot",
                {
                    selectionAdorned: false,
                    // 当selectionAdorned属性为true时，所选部件会自动获取为其创建的装饰。
                    // 默认情况下，选择装饰只是零件周围的简单蓝色框，并且是选定链接路径后的蓝色形状。
                    // 但是，您可以将selectionAdornmentTemplate设置为任意复杂的Adornment。 这样，当用户选择零件时，它可以显示用于执行各种命令的更多信息或按钮。
                    textEditable: false,
                    locationObjectName: "BODY"
                },
                new go.Binding("location", "loc", go.Point.parse).makeTwoWay(go.Point.stringify),
                // the main body consists of a Rectangle surrounding the text
                node_body(),
                // output port
                this._diagramNodeOutputPort(),
                // input port
                this._diagramNodeInputPort()
            );
        },
        // 定义流程图
        _diagramDefine: function () {
            return odoo.$$(go.Diagram, "diagramContainer",
                {
                    allowCopy: false,
                    allowSelect: session.is_approval_config,
                    initialContentAlignment: go.Spot.Top,
                    layout:
                        odoo.$$(go.LayeredDigraphLayout,
                            {
                                setsPortSpots: true,  // Links already know their fromSpot and toSpot
                                columnSpacing: 25,
                                layerSpacing: 35,
                                isInitial: true,
                                isOngoing: true
                            }),
                    validCycle: go.Diagram.CycleNotDirected, // 节点不能
                    // validCycle: go.Diagram.CycleAll,
                    "undoManager.isEnabled": false
                });
        },
        _addNodeAndLink: function () {
            var fromNode = obj.part;
            var diagram = fromNode.diagram;
            diagram.startTransaction("Add State");
            // get the node data for which the user clicked the button
            var fromData = fromNode.data;
            // create a new "State" data object, positioned off to the right of the fromNode
            var p = fromNode.location.copy();
            p.x += diagram.toolManager.draggingTool.gridSnapCellSize.width;
            var toData = {
                text: "new",
                loc: go.Point.stringify(p)
            };
            // add the new node data to the model
            var model = diagram.model;
            model.addNodeData(toData);
            // create a link data from the old node data to the new node data
            var linkdata = {
                from: model.getKeyForNodeData(fromData),
                to: model.getKeyForNodeData(toData)
            };
            // and add the link data to the model
            model.addLinkData(linkdata);
            // select the new Node
            var newnode = diagram.findNodeForData(toData);
            diagram.select(newnode);
            // snap the new node to a valid location
            newnode.location = diagram.toolManager.draggingTool.computeMove(newnode, p);
            // then account for any overlap
            this.shiftNodesToEmptySpaces();
            diagram.commitTransaction("Add State");
        },
        _lowLight: function () {
            if (this.diagram_OldTarget) {
                this.diagram_OldTarget.scale = 1.0;
                this.diagram_OldTarget = null;
            }
        },
        _renderDiagram: function(data) {
            this.diagram.model.nodeDataArray = data.nodes;
            this.diagram.model.linkDataArray = data.actions;
            $(this.diagramElement).show();
        }
    });

    var graygrad;
    $(function () {
        odoo.$$ = go.GraphObject.make;
        graygrad = odoo.$$(go.Brush, "Linear", {0: "white", 0.1: "whitesmoke", 0.9: "whitesmoke", 1: "lightgray"});
    })
});