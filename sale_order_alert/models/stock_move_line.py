# -*- coding: utf-8 -*-
from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self, vals):
        previous_states = {line.id: line.state for line in self}
        result = super().write(vals)

        if vals.get('state') == 'done':
            done_lines = self.filtered(
                lambda line: previous_states.get(line.id) != 'done' and line.state == 'done'
            )
            if done_lines:
                orders = (
                    done_lines.mapped('move_id.sale_line_id.order_id')
                    | done_lines.mapped('picking_id.sale_id')
                )
                orders = orders.filtered(lambda order: order)
                if orders:
                    existing_alerts = {
                        order.id: set(order.alert_log_ids.mapped('alert_type')) for order in orders
                    }
                    orders_to_notify = orders.filtered(
                        lambda order: 'shipped' not in existing_alerts.get(order.id, set())
                    )
                    if orders_to_notify:
                        orders_to_notify._auto_send_alert('shipped', message='shipped')

        return result
