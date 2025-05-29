# English comment: Odoo controller for batch import of orders and related data
from odoo import http
from odoo.http import request
import json

class ImportBatchController(http.Controller):
    @http.route('/import_batch/order', type='json', auth='user', methods=['POST'], csrf=False)
    def import_order_batch(self, **kwargs):
        # English comment: Parse JSON data from request
        data = kwargs.get('data')
        if isinstance(data, str):
            data = json.loads(data)
        elif not data:
            data = request.jsonrequest
        result = {'success': True, 'errors': [], 'created': {}, 'updated': {}}
        try:
            # English comment: Import partners (companies)
            partner_map = {}
            for partner in data.get('res_partner', []):
                partner_vals = partner.copy()
                partner_obj = request.env['res.partner'].sudo().search([('name', '=', partner['name']), ('type', '=', partner['type'])], limit=1)
                if partner_obj:
                    partner_obj.sudo().write(partner_vals)
                    partner_id = partner_obj.id
                    result['updated'].setdefault('res_partner', []).append(partner_id)
                else:
                    partner_id = request.env['res.partner'].sudo().create(partner_vals).id
                    result['created'].setdefault('res_partner', []).append(partner_id)
                partner_map[partner['name']] = partner_id

            # English comment: Import partner contacts
            for contact in data.get('res_partner_contact', []):
                contact_vals = contact.copy()
                parent_id = contact_vals.pop('parent_id', None)
                if parent_id and isinstance(parent_id, str):
                    contact_vals['parent_id'] = partner_map.get(parent_id, parent_id)
                contact_obj = request.env['res.partner'].sudo().search([
                    ('name', '=', contact['name']),
                    ('type', '=', 'contact'),
                    ('parent_id', '=', contact_vals.get('parent_id'))
                ], limit=1)
                if contact_obj:
                    contact_obj.sudo().write(contact_vals)
                    result['updated'].setdefault('res_partner_contact', []).append(contact_obj.id)
                else:
                    contact_id = request.env['res.partner'].sudo().create(contact_vals).id
                    result['created'].setdefault('res_partner_contact', []).append(contact_id)

            # English comment: Import products
            product_map = {}
            for product in data.get('product_product', []):
                product_obj = request.env['product.product'].sudo().search([('default_code', '=', product['default_code'])], limit=1)
                if product_obj:
                    product_obj.sudo().write(product)
                    product_id = product_obj.id
                    result['updated'].setdefault('product_product', []).append(product_id)
                else:
                    product_id = request.env['product.product'].sudo().create(product).id
                    result['created'].setdefault('product_product', []).append(product_id)
                product_map[product['default_code']] = product_id

            # English comment: Import units of measure
            uom_map = {}
            for uom in data.get('uom_uom', []):
                uom_obj = request.env['uom.uom'].sudo().search([('name', '=', uom['name'])], limit=1)
                if uom_obj:
                    uom_obj.sudo().write(uom)
                    uom_id = uom_obj.id
                    result['updated'].setdefault('uom_uom', []).append(uom_id)
                else:
                    uom_id = request.env['uom.uom'].sudo().create(uom).id
                    result['created'].setdefault('uom_uom', []).append(uom_id)
                uom_map[uom['name']] = uom_id

            # English comment: Import sale order
            so = data.get('sale_order')
            if so:
                so_vals = so.copy()
                # Map partner_id if needed
                if isinstance(so_vals.get('partner_id'), str):
                    so_vals['partner_id'] = partner_map.get(so_vals['partner_id'], so_vals['partner_id'])
                so_obj = request.env['sale.order'].sudo().search([('name', '=', so['name'])], limit=1)
                if so_obj:
                    so_obj.sudo().write(so_vals)
                    so_id = so_obj.id
                    result['updated'].setdefault('sale_order', []).append(so_id)
                else:
                    so_id = request.env['sale.order'].sudo().create(so_vals).id
                    result['created'].setdefault('sale_order', []).append(so_id)
            else:
                so_id = None

            # English comment: Import sale order lines
            for line in data.get('sale_order_line', []):
                line_vals = line.copy()
                # Map order_id, product_id, product_uom
                if isinstance(line_vals.get('order_id'), str):
                    line_vals['order_id'] = so_id
                if isinstance(line_vals.get('product_id'), str):
                    line_vals['product_id'] = product_map.get(line_vals['product_id'], line_vals['product_id'])
                if isinstance(line_vals.get('product_uom'), str):
                    line_vals['product_uom'] = uom_map.get(line_vals['product_uom'], line_vals['product_uom'])
                # Remove tax_id if empty
                if 'tax_id' in line_vals and not line_vals['tax_id']:
                    line_vals.pop('tax_id')
                # Try to find existing line
                line_obj = request.env['sale.order.line'].sudo().search([
                    ('order_id', '=', line_vals.get('order_id')),
                    ('product_id', '=', line_vals.get('product_id')),
                    ('name', '=', line_vals.get('name'))
                ], limit=1)
                if line_obj:
                    line_obj.sudo().write(line_vals)
                    result['updated'].setdefault('sale_order_line', []).append(line_obj.id)
                else:
                    line_id = request.env['sale.order.line'].sudo().create(line_vals).id
                    result['created'].setdefault('sale_order_line', []).append(line_id)

        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
        return result 