from odoo import http

class PingController(http.Controller):
    @http.route('/odoo/api/ping', type='http', auth='public', methods=['GET'], csrf=False)
    def test_ping(self):
        return "pong"
