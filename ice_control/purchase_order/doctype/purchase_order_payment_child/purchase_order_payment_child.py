# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PurchaseOrderPaymentChild(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Data | None
		default_account: DF.Link | None
		exchange_rate: DF.Float
		input_amount: DF.Float
		note: DF.LongText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Currency
		payment_type: DF.Link
		write_off_amount: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Purchase Order Payment Child"
