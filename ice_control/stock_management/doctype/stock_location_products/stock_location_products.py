# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StockLocationProducts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost: DF.Currency
		product_code: DF.Link
		product_name: DF.Data | None
		quantity: DF.Float
		stock_location: DF.Link | None
		unit: DF.Link | None
		vendor: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Stock Location Products"
