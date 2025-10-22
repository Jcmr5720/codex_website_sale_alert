{
    'name': 'Sale_Order_Alert',
    'version': '1.0.0',
    'category': 'Tools',
    'author': 'Juan Camilo Muñoz',
    'summary': 'Extra notificaciones a cliente',
    'depends': [
        'sale_management',
        'whatsapp_connector_sale'],
    'data': [
        'views/sale_order_views.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'GPL-3'
}
