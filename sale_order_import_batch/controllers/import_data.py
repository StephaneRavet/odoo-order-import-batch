# English comment: Odoo controller for batch import of orders and related data
from odoo import http
from odoo.http import request
import json
from datetime import datetime
import logging
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class ImportDataController(http.Controller):
    @http.route('/api/v1/sale/order/import/batch', type='json', auth='api_key', methods=['POST'], csrf=False)
    def import_order(self, **kwargs):
        try:
            content = request.jsonrequest
            if not content or not isinstance(content, list):
                return {'error': 'Invalid data format', 'code': 'INVALID_FORMAT'}

            order_data = content[0]['message']['content']
            
            # Validate required data
            validation_result = self._validate_order_data(order_data)
            if not validation_result['valid']:
                return {'error': validation_result['message'], 'code': 'VALIDATION_ERROR'}

            # Check if order already exists
            existing_order = self._check_existing_order(order_data['document']['orderNumber'])
            if existing_order:
                return {
                    'warning': 'Order already exists',
                    'order_id': existing_order.id,
                    'message': f'Order {order_data["document"]["orderNumber"]} already exists',
                    'code': 'ORDER_EXISTS'
                }

            # Create or update customer
            try:
                partner = self._create_or_update_partner(order_data['customer'])
            except Exception as e:
                return {'error': f'Error creating partner: {str(e)}', 'code': 'PARTNER_ERROR'}
            
            # Create order
            try:
                order = self._create_sale_order(order_data, partner)
            except Exception as e:
                return {'error': f'Error creating order: {str(e)}', 'code': 'ORDER_ERROR'}
            
            # Create order lines
            try:
                self._create_order_lines(order, order_data['orderLines'])
            except Exception as e:
                return {'error': f'Error creating order lines: {str(e)}', 'code': 'LINES_ERROR'}
            
            # Create training sessions
            try:
                self._create_training_sessions(order, order_data['training'])
            except Exception as e:
                return {'error': f'Error creating training sessions: {str(e)}', 'code': 'SESSIONS_ERROR'}

            return {
                'success': True,
                'order_id': order.id,
                'message': 'Order successfully imported',
                'code': 'SUCCESS'
            }

        except ValidationError as ve:
            _logger.error(f"Validation error: {str(ve)}")
            return {'error': str(ve), 'code': 'VALIDATION_ERROR'}
        except UserError as ue:
            _logger.error(f"User error: {str(ue)}")
            return {'error': str(ue), 'code': 'USER_ERROR'}
        except Exception as e:
            _logger.error(f"Error importing order: {str(e)}")
            return {'error': str(e), 'code': 'UNKNOWN_ERROR'}

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

    def _validate_order_data(self, data):
        """Detailed validation of order data"""
        required_fields = ['document', 'customer', 'orderLines', 'amounts']
        if not all(field in data for field in required_fields):
            return {'valid': False, 'message': 'Missing required fields'}

        # Document validation
        if not data['document'].get('orderNumber'):
            return {'valid': False, 'message': 'Missing order number'}
        if not data['document'].get('orderDate'):
            return {'valid': False, 'message': 'Missing order date'}

        # Customer validation
        if not data['customer'].get('companyName'):
            return {'valid': False, 'message': 'Missing company name'}
        if not data['customer'].get('siren'):
            return {'valid': False, 'message': 'Missing SIREN'}

        # Order lines validation
        if not data['orderLines']:
            return {'valid': False, 'message': 'No order lines'}
        for line in data['orderLines']:
            if not line.get('reference'):
                return {'valid': False, 'message': 'Missing product reference'}
            if not line.get('quantity') or line['quantity'] <= 0:
                return {'valid': False, 'message': 'Invalid quantity'}
            if not line.get('unitPrice') or line['unitPrice'] <= 0:
                return {'valid': False, 'message': 'Invalid unit price'}

        # Amounts validation
        if not data['amounts'].get('totalExclTax'):
            return {'valid': False, 'message': 'Missing total amount'}

        # Training sessions validation
        if data.get('training'):
            if not data['training'].get('sessions'):
                return {'valid': False, 'message': 'No training sessions defined'}
            for session in data['training']['sessions']:
                if not session.get('date'):
                    return {'valid': False, 'message': 'Missing session date'}
                if not session.get('startTimes') or not session.get('endTimes'):
                    return {'valid': False, 'message': 'Missing session times'}

        return {'valid': True}

    def _check_existing_order(self, order_number):
        """Check if an order already exists with this number"""
        return request.env['sale.order'].search([
            ('client_order_ref', '=', order_number)
        ], limit=1)

    def _create_or_update_partner(self, customer_data):
        partner_obj = request.env['res.partner']
        
        # Search by SIREN (unique identifier)
        siren = customer_data['siren'].replace(' ', '')
        partner = partner_obj.search([('siren', '=', siren)], limit=1)
        
        if not partner:
            # Check by SIRET if available
            if customer_data.get('siret'):
                siret = customer_data['siret'][0].replace(' ', '')
                partner = partner_obj.search([('siret', '=', siret)], limit=1)
            
            # Check by VAT number
            if not partner and customer_data.get('tva'):
                partner = partner_obj.search([('vat', '=', customer_data['tva'])], limit=1)
        
        partner_vals = {
            'name': customer_data['companyName'],
            'siren': siren,
            'siret': customer_data['siret'][0].replace(' ', '') if customer_data['siret'] else False,
            'vat': customer_data['tva'],
            'street': customer_data['addresses'][0]['addressLine'],
            'zip': customer_data['addresses'][0]['postalCode'],
            'city': customer_data['addresses'][0]['city'],
            'country_id': request.env['res.country'].search([('name', '=', customer_data['addresses'][0]['country'])], limit=1).id,
            'email': customer_data['billingEmail'],
            'phone': customer_data.get('contact', {}).get('phone', False),
            'customer_rank': 1,
            'type': 'contact',
            'company_type': 'company',
            'active': True,
        }

        if not partner:
            partner = partner_obj.create(partner_vals)
        else:
            partner.write(partner_vals)
        
        return partner

    def _create_sale_order(self, order_data, partner):
        sale_order_obj = request.env['sale.order']
        
        return sale_order_obj.create({
            'partner_id': partner.id,
            'client_order_ref': order_data['document']['orderNumber'],
            'date_order': datetime.strptime(order_data['document']['orderDate'], '%Y-%m-%dT%H:%M:%SZ'),
            'payment_term_id': self._get_payment_term(order_data['paymentTerms']),
            'amount_untaxed': order_data['amounts']['totalExclTax'],
            'amount_tax': order_data['amounts']['totalVAT'],
            'amount_total': order_data['amounts']['totalInclTax'],
            'state': 'sale',
            'company_id': request.env.company.id,
            'user_id': request.env.user.id,
            'team_id': request.env['crm.team'].search([], limit=1).id,
        })

    def _create_order_lines(self, order, order_lines):
        sale_order_line_obj = request.env['sale.order.line']
        
        for sequence, line in enumerate(order_lines, start=10):
            # Check if line already exists
            existing_line = sale_order_line_obj.search([
                ('order_id', '=', order.id),
                ('product_id.default_code', '=', line['reference'])
            ], limit=1)
            
            if not existing_line:
                product = self._get_or_create_product(line)
                sale_order_line_obj.create({
                    'order_id': order.id,
                    'product_id': product.id,
                    'name': line['label'],
                    'product_uom_qty': line['quantity'],
                    'product_uom': self._get_uom(line['unit']),
                    'price_unit': line['unitPrice'],
                    'discount': line['discountPercent'],
                    'price_subtotal': line['totalExclTax'],
                    'sequence': sequence,
                })

    def _create_training_sessions(self, order, training_data):
        training_session_obj = request.env['training.session']
        
        for session in training_data['sessions']:
            # Check if session already exists
            existing_session = training_session_obj.search([
                ('sale_order_id', '=', order.id),
                ('date', '=', session['date']),
                ('start_time', '=', session['startTimes'][0]),
                ('end_time', '=', session['endTimes'][0])
            ], limit=1)
            
            if not existing_session:
                training_session_obj.create({
                    'sale_order_id': order.id,
                    'name': training_data['title'],
                    'trainer_id': self._get_or_create_trainer(training_data['trainer']),
                    'date': session['date'],
                    'start_time': session['startTimes'][0],
                    'end_time': session['endTimes'][0],
                    'location': training_data['location'],
                    'modality': training_data['modality'],
                    'state': 'confirmed',
                    'company_id': request.env.company.id,
                })

    def _get_payment_term(self, payment_terms):
        payment_term_obj = request.env['account.payment.term']
        term = payment_term_obj.search([('name', '=', payment_terms)], limit=1)
        if not term:
            _logger.warning(f"Payment term not found: {payment_terms}")
            return payment_term_obj.search([], limit=1)
        return term

    def _get_or_create_product(self, line_data):
        product_obj = request.env['product.product']
        # Check by internal reference (unique identifier)
        product = product_obj.search([('default_code', '=', line_data['reference'])], limit=1)
        
        if not product:
            product = product_obj.create({
                'name': line_data['label'],
                'default_code': line_data['reference'],
                'type': 'service',
                'categ_id': request.env.ref('product.product_category_services').id,
                'list_price': line_data['unitPrice'],
                'standard_price': line_data['unitPrice'],  # Cost price
                'uom_id': self._get_uom(line_data['unit']).id,
                'uom_po_id': self._get_uom(line_data['unit']).id,
                'invoice_policy': 'order',
                'purchase_method': 'purchase',
                'active': True,
            })
        
        return product

    def _get_uom(self, unit_name):
        uom_obj = request.env['uom.uom']
        uom = uom_obj.search([('name', '=', unit_name)], limit=1)
        if not uom:
            _logger.warning(f"Unit of measure not found: {unit_name}")
            return uom_obj.search([('name', '=', 'Unit')], limit=1)
        return uom

    def _get_or_create_trainer(self, trainer_name):
        partner_obj = request.env['res.partner']
        # Check by name (unique identifier for trainers)
        trainer = partner_obj.search([
            ('name', '=', trainer_name),
            ('is_trainer', '=', True)
        ], limit=1)
        
        if not trainer:
            trainer = partner_obj.create({
                'name': trainer_name,
                'is_trainer': True,
                'type': 'contact',
                'company_type': 'person',
                'active': True,
            })
        
        return trainer 