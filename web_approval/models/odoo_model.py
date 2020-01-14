# -*- coding: utf-8 -*-
import logging
import uuid
from psycopg2 import ProgrammingError

from odoo import models, api, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

Model = models.Model
original_setup_base = Model._setup_base


@api.model
def _setup_base(self):
    original_setup_base(self)
    setup_approval_state_fields(self)


def setup_approval_state_fields(self):
    """安装审批状态字段"""

    def add(name, field):
        if name not in self._fields:
            self._add_field(name, field)

    self._cr.execute("SELECT COUNT(*) FROM pg_class WHERE relname = 'approval_flow'")
    table = self._cr.fetchall()
    if table[0][0] > 0:
        self._cr.execute(
            "SELECT im.model FROM approval_flow af JOIN ir_model im ON af.model_id = im.id WHERE im.model = '%s'" % self._name)
        res = self._cr.fetchall()
        if len(res) != 0:
            add('doc_approval_state', fields.Char(string=u'审批状态', compute='_compute_doc_approval_state'))


@api.one
def _compute_doc_approval_state(self):
    res_state = self.env['record.approval.state'].search([('model', '=', self._name), ('res_id', '=', self.id)])
    if res_state:
        approval_state = res_state.approval_state
        if approval_state == 'draft' or not approval_state:
            self.doc_approval_state = u'未送审'
        elif approval_state == 'complete':
            self.doc_approval_state = u'审批完成'
        elif approval_state == 'pause':
            self.doc_approval_state = u'暂停审批'
        elif approval_state == 'cancel':
            self.doc_approval_state = u'取消审批'
        else:
            wait_users = u','.join([wait_approval.user_id.sudo().name for wait_approval in
                                    self.env['wait.approval'].search(
                                        [('model_name', '=', self._name), ('res_id', '=', self.id),
                                         ('state', '=', 'running')])])
            self.doc_approval_state = u'等待<span style="color:red">%s</span>审批' % wait_users
    else:
        self.doc_approval_state = u' '


Model._setup_base = _setup_base
setattr(Model, '_compute_doc_approval_state', _compute_doc_approval_state)

create_origin = models.BaseModel.create


@api.model_create_multi
@api.returns('self', lambda value: value.id)
def create(self, vals_list):
    record = create_origin(self, vals_list)
    for res in record:
        create_approval_flow(self, res)  # 创建审批流程
    return record


def create_approval_flow(self, record):
    """创建审批流程实例及节点"""
    approval_flow = record._get_approval_flow()
    # 没有对应的流程
    if not approval_flow:
        return

    model = self._name
    res_id = record.id

    # 模块卸载重新安装，有可能不能删除对应的ir.model，则导致record.approval.state和关联的审批信息没有删除，在新建记录时，再删除相关的
    obj = self.env['record.approval.state']
    instance_obj = self.env['approval.flow.instance']
    res_state = obj.search([('model', '=', model), ('res_id', '=', res_id)])
    if res_state:
        res_state.unlink()
        instance_obj.search([('model_name', '=', model.model), ('res_id', '=', res_id)]).unlink()

    # 创建审批状态
    obj.create({
        'model': model,
        'res_id': res_id,
        # 'flow_id': approval_flow.id
    })


models.BaseModel.create = create

write_origin = models.BaseModel.write


@api.multi
def write(self, vals):
    # if self.env['ir.module.module'].search_count([('name', '=', 'web_approval'), ('state', '=', 'installed')]):
    #     for rec in self:
    #         approval_state = self.env['record.approval.state'].search(
    #             [('model', '=', self._name), ('res_id', '=', rec.id)])
    #         if approval_state and approval_state.approval_state not in [False, 'cancel']:  # 审批中
    #             _is_set_approval(self, vals)
    approval_write(self, vals)
    return write_origin(self, vals)


def _is_set_approval(self, vals):
    """
    :param self:
    :return:
    """
    state = vals.get('state')
    if state:
        for rec in self:
            record_approval_state = self.env['record.approval.state'].search(
                [('model', '=', rec._name), ('res_id', '=', rec.id)])
            if record_approval_state and not record_approval_state.is_commit_approval:
                raise ValidationError("当前单据设置了审批流程，请提交审批！")


def approval_write(self, vals):
    """审批后不能执行修改动作"""
    res_state_obj = self.env.get('record.approval.state')
    if res_state_obj is None:
        return

    # 关注与取消关注处理
    if len(vals.keys()) == 1 and list(vals.keys())[0] == 'message_follower_ids':
        return

    name = uuid.uuid1().hex
    self._cr.execute('SAVEPOINT "%s"' % name)
    try:
        for res in self:
            # 文档在审批过程中，不能删除
            res_state = res_state_obj.search([('model', '=', self._name), ('res_id', '=', res.id)])
            if not res_state:
                continue

            if res_state.approval_state in ['active', 'pause']:
                raise ValidationError(u'单据在审批过程中，不能修改！')

            elif res_state.approval_state == 'complete':
                context = self._context or {}
                # if 'approval_callback' not in context:
                #     raise ValidationError(u'单据审批完成，不能修改！')
                if context.get('approval_callback') == 0:
                    raise ValidationError(u'该方法在审批完成后不允许执行！')
    except ProgrammingError as e:
        _logger.error(u'修改model: %s, id: %s出错', self._name, self.ids)
        self._cr.execute('ROLLBACK TO SAVEPOINT "%s"' % name)
    else:
        self._cr.execute('RELEASE SAVEPOINT "%s"' % name)


models.BaseModel.write = write

unlink_origin = models.BaseModel.unlink


@api.multi
def unlink(self):
    approval_unlink(self)
    return unlink_origin(self)


def approval_unlink(self):
    """审批后不能执行删除动作"""
    res_state_obj = self.env.get('record.approval.state')
    if res_state_obj is None:
        return

    name = uuid.uuid1().hex
    self._cr.execute('SAVEPOINT "%s"' % name)
    context = self._context or {}

    try:
        for res in self:
            # 文档在审批过程中，不能删除
            res_state = res_state_obj.search([('model', '=', self._name), ('res_id', '=', res.id)])
            if not res_state:
                continue

            if res_state.approval_state in ['active', 'pause']:
                if 'approval_callback' not in context:
                    raise ValidationError(u'单据在审批过程中，不能删除！')

            if res_state.approval_state in ['complete']:
                if 'approval_callback' not in context:
                    raise ValidationError(u'单据审批完成，不能删除！')

            # 删除审批状态
            res_state.unlink()

            # # 删除审批实例
            # self.env['approval.flow.instance'].search([('model_name', '=', self._name), ('res_id', '=', res.id)]).unlink()


    except ProgrammingError as e:
        _logger.error(u'删除model: %s, id: %s出错', self._name, self.ids)
        self._cr.execute('ROLLBACK TO SAVEPOINT "%s"' % name)
    else:
        self._cr.execute('RELEASE SAVEPOINT "%s"' % name)


models.BaseModel.unlink = unlink
