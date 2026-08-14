# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PaymentTypeGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		is_bank: DF.Check
		payment_type_group_en: DF.Data | None
		payment_type_group_kh: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Payment Type Group"
