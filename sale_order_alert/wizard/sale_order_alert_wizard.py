# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderAlertWizard(models.TransientModel):
    _name = 'sale.order.alert.wizard'
    _description = 'Sale Order Alert Wizard'

    alert_type = fields.Selection(
        selection=lambda self: self.env['sale.order']._get_alert_selection(),
        required=True,
    )
    message = fields.Text(required=True)
    order_id = fields.Many2one(
        'sale.order',
        required=True,
        default=lambda self: self.env['sale.order'].browse(
            self.env.context.get('default_order_id') or self.env.context.get('active_id')
        ),
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        sale_order_model = self.env['sale.order']
        order = sale_order_model.browse(
            self.env.context.get('default_order_id') or self.env.context.get('active_id')
        )
        selection = order._get_alert_selection() if order else sale_order_model._get_alert_selection()
        if selection:
            alert_type = defaults.get('alert_type') or next(
                (item[0] for item in selection if item and item[0]),
                False,
            )
            if alert_type:
                defaults.setdefault('alert_type', alert_type)
                if order:
                    defaults.setdefault('message', order._get_alert_message(alert_type))
                else:
                    defaults.setdefault('message', sale_order_model._get_alert_message(alert_type))
        return defaults

    @api.onchange('alert_type')
    def _onchange_alert_type(self):
        if self.alert_type:
            order_model = self.order_id or self.env['sale.order']
            self.message = order_model._get_alert_message(self.alert_type)

    def action_send_alert(self):
        self.ensure_one()
        if not self.order_id:
            raise UserError(_('No hay una orden relacionada para enviar la alerta.'))
        message = self.message or self.order_id._get_alert_message(self.alert_type)
        self.order_id._send_alert(self.alert_type, message=message)
        return {'type': 'ir.actions.act_window_close'}
