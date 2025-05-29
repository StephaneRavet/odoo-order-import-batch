# sale_order_import-batch_2

> Compatible Odoo version: **18**

This Odoo module provides automated order import functionality via a REST API. It handles complete data integration into Odoo, including customers, orders, order lines, and training sessions.

## Features

- Order import via REST API
- Automatic customer management (create/update)
- Sales order creation
- Order line management
- Training session creation
- Duplicate checking
- Complete data validation
- Detailed error handling

## Project Structure

```
sale_order_import-batch_2/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── main.py
│   └── ping.py
├── README.md
```

## Installation

1. Copy the module to Odoo's `addons` directory
2. Update the module list in Odoo
3. Install the "Sale Order Import Batch" module

## API Usage

### Test Endpoint
```
GET /api/ping
```

#### Response
```json
{
  "status": "ok",
  "message": "pong"
}
```

### Import Endpoint
```
POST /api/v1/order/import
```

### Authentication
- Type: API Key
- Header: `Authorization: Bearer <api_key>`

### Data Format
```json
[
  {
    "message": {
      "content": {
        "document": {
          "orderNumber": "REF-123",
          "orderDate": "2024-03-19T00:00:00Z"
        },
        "customer": {
          "companyName": "Company",
          "siren": "123 456 789",
          "tva": "FR12345678900"
        },
        "orderLines": [
          {
            "reference": "PROD-001",
            "label": "Training",
            "quantity": 1,
            "unitPrice": 1000
          }
        ],
        "training": {
          "sessions": [
            {
              "date": "2024-03-20",
              "startTimes": ["09:00"],
              "endTimes": ["17:00"]
            }
          ]
        }
      }
    }
  }
]
```

### Responses

#### Success
```json
{
  "success": true,
  "order_id": 123,
  "message": "Order successfully imported",
  "code": "SUCCESS"
}
```

#### Error
```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## Error Codes

- `INVALID_FORMAT`: Invalid data format
- `VALIDATION_ERROR`: Data validation error
- `ORDER_EXISTS`: Order already exists
- `PARTNER_ERROR`: Error creating partner
- `ORDER_ERROR`: Error creating order
- `LINES_ERROR`: Error creating order lines
- `SESSIONS_ERROR`: Error creating sessions
- `USER_ERROR`: User error
- `UNKNOWN_ERROR`: Unknown error

## Security

- API Key authentication
- Input data validation
- Odoo access rights management
- Error logging

## Dependencies

- Odoo 18
- Training module (for sessions)