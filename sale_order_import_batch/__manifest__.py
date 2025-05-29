{
    "name": "Sale Order Import Batch",
    "version": "1.0.0",
    "summary": "Batch import of orders",
    "category": "Tools",
    "author": "Stéphane Ravet",
    "website": "https://github.com/StephaneRavet/odoo-sale-order-import-batch",
    "depends": ["base", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir.config_parameter.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
    "license": "LGPL-3",
}
