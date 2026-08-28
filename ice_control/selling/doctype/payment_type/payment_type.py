# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PaymentType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		enabled: DF.Check
		is_default: DF.Check
		payment_type: DF.Data | None
		payment_type_group: DF.Link | None
		sort_order: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Payment Type"
