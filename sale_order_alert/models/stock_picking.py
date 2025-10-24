# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        sale_orders = self.env['sale.order']
        state_to_done = vals.get('state')
        if state_to_done:
            target_state = vals['state']
            if target_state == 'done':
                sale_orders = self.filtered(lambda picking: picking.state != 'done' and picking.sale_id).mapped('sale_id')
        result = super().write(vals)
        if state_to_done == 'done' and sale_orders:
            for order in sale_orders:
                order._auto_send_alert('shipped')
                delivery_status = getattr(order, 'delivery_status', False)
                if delivery_status == 'delivered':
                    order._auto_send_alert('delivered')
        return result
