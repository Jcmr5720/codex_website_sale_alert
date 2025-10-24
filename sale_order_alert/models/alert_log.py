# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderAlertLog(models.Model):
    _name = 'sale.order.alert.log'
    _description = 'Sale Order Alert Log'
    _order = 'sent_at desc, id desc'

    order_id = fields.Many2one(
        'sale.order',
        required=True,
        ondelete='cascade',
    )
    alert_type = fields.Selection(
        selection=lambda self: self.env['sale.order']._get_alert_selection(),
        required=True,
        index=True,
    )
    message = fields.Text(required=True)
    sent_at = fields.Datetime(default=fields.Datetime.now, required=True)
