# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VendorProductPrice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		product: DF.Link | None
		product_name: DF.Data | None
		stock_location: DF.Link | None
		unit: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Vendor Product Price"
