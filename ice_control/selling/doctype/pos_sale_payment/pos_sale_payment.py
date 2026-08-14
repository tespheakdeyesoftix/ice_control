# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class POSSalePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		exchange_rate: DF.Data | None
		input_amount: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Currency
		payment_type: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "POS Sale Payment"
