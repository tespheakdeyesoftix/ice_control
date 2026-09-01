# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
class PaymentType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.
	from typing import TYPE_CHECKING
	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.accounting.doctype.has_default_account.has_default_account import HasDefaultAccount

		currency: DF.Link | None
		default_account: DF.Table[HasDefaultAccount]
		enabled: DF.Check
		is_default: DF.Check
		payment_type: DF.Data | None
		payment_type_group: DF.Link | None
		sort_order: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Payment Type"
	def validate(self):
		old_doc = self.get_doc_before_save()
		if self.is_new():
			if self.is_default:
				frappe.db.sql("update `tabPayment Type` set is_default=0 where name != %s", self.name)
				frappe.db.commit()
				frappe.msgprint(f"Payment Type {self.name} is set as default payment type.")
		else:
			if self.is_default != old_doc.is_default:
				frappe.db.sql("update `tabPayment Type` set is_default=0 where name != %s", self.name)
				frappe.db.commit()
				frappe.msgprint(f"Payment Type {self.name} is set as default payment type.")