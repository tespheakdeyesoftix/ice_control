# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InventoryTransactions(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		balance: DF.Float
		base_unit: DF.Link | None
		cost: DF.Currency
		current_cost: DF.Currency
		in_quantity: DF.Float
		multiplier: DF.Float
		note: DF.LongText | None
		opening_quantity: DF.Float
		out_quantity: DF.Float
		posting_date: DF.Date | None
		product_code: DF.Link | None
		product_name: DF.Data | None
		quantity: DF.Float
		ref_docname: DF.DynamicLink | None
		ref_doctype: DF.Link | None
		stock_location: DF.Link | None
		unit: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Inventory Transactions"
