# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AuditTrailLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		audit_trail_type: DF.Data | None
		description: DF.SmallText | None
		outlet: DF.Link | None
		posting_date: DF.Datetime | None
		ref_doc_name: DF.Data | None
		ref_doctype: DF.Data | None
		station: DF.Link | None
		username: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Audit Trail Log"

	def validate(self):
		self.username =frappe.get_cached_value("User",frappe.session.user,"full_name")
		self.posting_date = frappe.utils.now()

@frappe.whitelist(methods="POST")
def create_audit_trail_log(data):
	data["doctype"] = "Audit Trail Log"
	frappe.get_doc(data).insert(ignore_permissions=True)
