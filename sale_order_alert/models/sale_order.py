# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    def action_inform_customer(self):
        message = _('Tu pedido esta siendo alistado')
        for order in self:
            if order.invoice_status != 'invoiced':
                raise UserError(_('Solo se puede informar cuando la orden está facturada.'))
            conversation = order._ensure_whatsapp_conversation()
            if not conversation:
                raise UserError(_('No se pudo encontrar o crear una conversación de WhatsApp.'))
            conversation.send_message_bus_release(
                {
                    'ttype': 'text',
                    'from_me': True,
                    'text': message,
                },
                conversation.status or 'done',
                check_access=False,
            )
        return True
