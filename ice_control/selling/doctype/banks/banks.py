# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
class Banks(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_name: DF.Data | None
		bank_number: DF.Data | None
		enabled: DF.Check
		is_default: DF.Check
	# end: auto-generated types

	_DOCTYPE_NAME = "Banks"
	def validate(self):
		old_doc = self.get_doc_before_save()
		if self.is_new():
			if self.is_default:
				frappe.db.sql("update `tabBanks` set is_default=0 where name != %s", self.name)
				frappe.db.commit()
				frappe.msgprint(f"Bank {self.name} is set as default bank.")
		else:
			if self.is_default != old_doc.is_default:
				frappe.db.sql("update `tabBanks` set is_default=0 where name != %s", self.name)
				frappe.db.commit()
				frappe.msgprint(f"Bank {self.name} is set as default bank.")