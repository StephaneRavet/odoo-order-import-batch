from odoo import http

@http.route('/api/ping', type='http', auth='public')
def test_ping(self):
    return "pong"
