from odoo import http

class PingController(http.Controller):
    @http.route('/api/ping', type='http', auth='public')
    def test_ping(self):
        return "pong"
