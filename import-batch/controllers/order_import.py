from odoo import http
from odoo.http import request
import json
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class OrderImportController(http.Controller):
    @http.route('/api/v1/order/import-batch', type='json', auth='api_key', methods=['POST'], csrf=False)
    def import_order(self, **kwargs):
        try:
            content = request.jsonrequest
            if not content or not isinstance(content, list):
                return {'error': 'Format de données invalide'}

            order_data = content[0]['message']['content']
            
            # Validation des données requises
            if not self._validate_order_data(order_data):
                return {'error': 'Données de commande incomplètes'}

            # Création du partenaire client
            partner = self._create_or_update_partner(order_data['customer'])
            
            # Création de la commande
            order = self._create_sale_order(order_data, partner)
            
            # Création des lignes de commande
            self._create_order_lines(order, order_data['orderLines'])
            
            # Création des sessions de formation
            self._create_training_sessions(order, order_data['training'])

            return {
                'success': True,
                'order_id': order.id,
                'message': 'Commande importée avec succès'
            }

        except Exception as e:
            _logger.error(f"Erreur lors de l'importation de la commande: {str(e)}")
            return {'error': str(e)}

    def _validate_order_data(self, data):
        required_fields = ['document', 'customer', 'orderLines', 'amounts']
        return all(field in data for field in required_fields)

    def _create_or_update_partner(self, customer_data):
        partner_obj = request.env['res.partner']
        
        # Recherche par SIREN
        partner = partner_obj.search([('siren', '=', customer_data['siren'].replace(' ', ''))], limit=1)
        
        if not partner:
            partner = partner_obj.create({
                'name': customer_data['companyName'],
                'siren': customer_data['siren'].replace(' ', ''),
                'siret': customer_data['siret'][0].replace(' ', '') if customer_data['siret'] else False,
                'vat': customer_data['tva'],
                'street': customer_data['addresses'][0]['addressLine'],
                'zip': customer_data['addresses'][0]['postalCode'],
                'city': customer_data['addresses'][0]['city'],
                'country_id': request.env['res.country'].search([('name', '=', customer_data['addresses'][0]['country'])], limit=1).id,
                'email': customer_data['billingEmail'],
                'phone': customer_data.get('contact', {}).get('phone', False),
                'customer_rank': 1,
            })
        
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
        })

    def _create_order_lines(self, order, order_lines):
        sale_order_line_obj = request.env['sale.order.line']
        
        for line in order_lines:
            product = self._get_or_create_product(line)
            sale_order_line_obj.create({
                'order_id': order.id,
                'product_id': product.id,
                'name': line['label'],
                'product_uom_qty': line['quantity'],
                'product_uom': self._get_uom(line['unit']),
                'price_unit': line['unitPrice'],
                'discount': line['discountPercent'],
            })

    def _create_training_sessions(self, order, training_data):
        training_session_obj = request.env['training.session']
        
        for session in training_data['sessions']:
            training_session_obj.create({
                'sale_order_id': order.id,
                'name': training_data['title'],
                'trainer_id': self._get_or_create_trainer(training_data['trainer']),
                'date': session['date'],
                'start_time': session['startTimes'][0],
                'end_time': session['endTimes'][0],
                'location': training_data['location'],
                'modality': training_data['modality'],
            })

    def _get_payment_term(self, payment_terms):
        # Logique pour trouver ou créer les conditions de paiement
        payment_term_obj = request.env['account.payment.term']
        return payment_term_obj.search([('name', '=', payment_terms)], limit=1)

    def _get_or_create_product(self, line_data):
        product_obj = request.env['product.product']
        product = product_obj.search([('default_code', '=', line_data['reference'])], limit=1)
        
        if not product:
            product = product_obj.create({
                'name': line_data['label'],
                'default_code': line_data['reference'],
                'type': 'service',
                'categ_id': request.env.ref('product.product_category_services').id,
            })
        
        return product

    def _get_uom(self, unit_name):
        uom_obj = request.env['uom.uom']
        return uom_obj.search([('name', '=', unit_name)], limit=1)

    def _get_or_create_trainer(self, trainer_name):
        partner_obj = request.env['res.partner']
        trainer = partner_obj.search([('name', '=', trainer_name)], limit=1)
        
        if not trainer:
            trainer = partner_obj.create({
                'name': trainer_name,
                'is_trainer': True,
            })
        
        return trainer 