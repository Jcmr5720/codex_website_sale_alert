# -*- coding: utf-8 -*-
import logging
from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ALERT_MESSAGES = OrderedDict({
        'packing': {
            'label': _('Alistamiento'),
            'message': _('Tu pedido está siendo alistado.'),
        },
        'shipped': {
            'label': _('Enviado'),
            'message': _('Tu pedido ha sido enviado.'),
        },
        'delivered': {
            'label': _('Entregado'),
            'message': _('Tu pedido ha sido entregado.'),
        },
    })

    alert_log_ids = fields.One2many(
        'sale.order.alert.log',
        'order_id',
        string='Alert Logs',
    )
    alert_sent_type_ids = fields.Char(
        compute='_compute_alert_sent_type_ids',
        string='Alert Types Sent',
    )

    def _ensure_whatsapp_conversation(self):
        self.ensure_one()
        conversation = self.conversation_id
        if not conversation and self.partner_id:
            partner_conversation = self.partner_id.contact_ids[:1]
            if partner_conversation:
                conversation = partner_conversation
        if not conversation:
            partner = self.partner_id
            if not partner:
                raise UserError(_('No se pudo determinar el cliente para la orden.'))
            number = partner.mobile or partner.phone
            if not number:
                raise UserError(_('El cliente no tiene un número de teléfono configurado.'))
            connector = self.env['acrux.chat.connector'].search([], limit=1)
            if not connector:
                raise UserError(_('No hay un conector de WhatsApp configurado.'))
            conversation_sudo = self.env['acrux.chat.conversation'].sudo().conversation_create(
                partner, connector.id, number
            )
            conversation = conversation_sudo.with_env(self.env)
        if conversation and not self.conversation_id:
            self.conversation_id = conversation.id
        return conversation

    @api.depends('alert_log_ids.alert_type')
    def _compute_alert_sent_type_ids(self):
        for order in self:
            keys = sorted(set(order.alert_log_ids.mapped('alert_type')))
            order.alert_sent_type_ids = ','.join(keys) if keys else False

    @api.model
    def _get_alert_definitions(self):
        """Return the alert configuration dictionary."""
        return self.ALERT_MESSAGES

    @api.model
    def _get_alert_selection(self):
        return [(key, values['label']) for key, values in self._get_alert_definitions().items()]

    @api.model
    def _get_alert_message(self, alert_type):
        definitions = self._get_alert_definitions()
        if alert_type not in definitions:
            raise UserError(_('Tipo de alerta desconocido.'))
        return definitions[alert_type]['message']

    @api.model
    def _get_alert_label(self, alert_type):
        definitions = self._get_alert_definitions()
        return definitions.get(alert_type, {}).get('label', alert_type)

    def _send_alert(self, alert_type, message=None):
        self.ensure_one()
        if alert_type not in dict(self._get_alert_selection()):
            raise UserError(_('Tipo de alerta desconocido.'))
        if self.invoice_status != 'invoiced' and alert_type not in {'packing', 'shipped'}:
            raise UserError(_('Solo se puede informar cuando la orden está facturada.'))

        conversation = self._ensure_whatsapp_conversation()
        if not conversation:
            raise UserError(_('No se pudo encontrar o crear una conversación de WhatsApp.'))

        text = message or self._get_alert_message(alert_type)
        conversation.send_message_bus_release(
            {
                'ttype': 'text',
                'from_me': True,
                'text': text,
            },
            conversation.status or 'done',
            check_access=False,
        )

        self.env['sale.order.alert.log'].create({
            'order_id': self.id,
            'alert_type': alert_type,
            'message': text,
        })

        return True

    def _auto_send_alert(self, alert_type, message=None):
        existing_alerts = {
            order.id: set(order.alert_log_ids.mapped('alert_type')) for order in self
        }
        for order in self:
            if alert_type in existing_alerts.get(order.id, set()):
                continue
            try:
                order._send_alert(alert_type, message=message)
            except UserError as error:
                _logger.info(
                    'Se omitió el envío automático de la alerta %(alert_type)s para '
                    'la orden %(order)s: %(error)s',
                    {
                        'alert_type': alert_type,
                        'order': order.name or order.id,
                        'error': error,
                    },
                )
        return True

    def action_inform_customer(self):
        for order in self:
            order._send_alert('packing')
        return True

    def write(self, vals):
        previous_states = {order.id: order.state for order in self}
        to_inform = self.filtered(lambda order: order.invoice_status != 'invoiced')
        result = super().write(vals)

        if to_inform:
            to_inform.filtered(lambda order: order.invoice_status == 'invoiced')._auto_send_alert(
                'packing',
                message=_('Tu pedido se está alistando'),
            )

        transitioned_orders = self.filtered(
            lambda order: previous_states.get(order.id) not in {'sale', 'done'}
            and order.state in {'sale', 'done'}
        )
        if transitioned_orders:
            transitioned_orders._auto_send_alert('packing', message=_('Tu pedido se está alistando'))

        return result
