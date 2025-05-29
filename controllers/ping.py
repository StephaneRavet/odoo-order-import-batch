from odoo import http
import json

class PingController(http.Controller):
    @http.route('/api/ping', type='json', auth='public', methods=['GET'], csrf=False)
    def test_ping(self):
        print("ping-pong")
        return http.Response(
            json.dumps({"status": "ok", "message": "pong"}),
            content_type='application/json'
        )
