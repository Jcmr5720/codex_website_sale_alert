# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

from odoo.exceptions import UserError
from odoo.tests import common


class TestSaleOrderAlert(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'mobile': '+573001112233',
        })
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        # Force invoiced status for the purpose of the tests.
        self.order.sudo().write({'invoice_status': 'invoiced'})

    def test_default_message_selection(self):
        message = self.order._get_alert_message('packing')
        self.assertTrue(message)
        self.assertIn('pedido', message)

    def test_send_alert_creates_log(self):
        dummy_conversation = Mock()
        with patch.object(type(self.order), '_ensure_whatsapp_conversation', return_value=dummy_conversation):
            self.order._send_alert('packing')

        dummy_conversation.send_message_bus_release.assert_called_once()
        logs = self.env['sale.order.alert.log'].search([('order_id', '=', self.order.id)])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.alert_type, 'packing')
        self.assertTrue(self.order.alert_sent_type_ids)

    def test_unknown_alert_type(self):
        with self.assertRaises(UserError):
            self.order._send_alert('unknown')
