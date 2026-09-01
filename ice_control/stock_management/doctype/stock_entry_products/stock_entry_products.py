# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StockEntryProducts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Currency
		default_stock_location: DF.Link | None
		is_inventory_product: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		product_code: DF.Link
		product_name: DF.Data | None
		quantity: DF.Float
		total_cost: DF.Currency
		unit: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Stock Entry Products"
