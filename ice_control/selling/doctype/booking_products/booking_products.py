# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BookingProducts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		note: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		price: DF.Currency
		product_code: DF.Link | None
		product_name: DF.Data | None
		quantity: DF.Float
		total_amount: DF.Currency
		transaction_type: DF.Literal["Sale", "Borrow"]
		unit: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Booking Products"
