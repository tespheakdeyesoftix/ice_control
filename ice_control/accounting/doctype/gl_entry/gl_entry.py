# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GLEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		account_type: DF.Data | None
		against: DF.SmallText | None
		against_voucher_no: DF.Link | None
		against_voucher_type: DF.Link | None
		amended_from: DF.Link | None
		amount: DF.Float
		credit_amount: DF.Float
		debit_amount: DF.Float
		is_cancelled: DF.Check
		outlet: DF.Link
		party: DF.Data | None
		party_name: DF.Data | None
		party_type: DF.Link | None
		posting_date: DF.Date | None
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		remark: DF.LongText | None
		sale_id: DF.Data | None
		transaction_type: DF.Literal["Receivable", "Payment", "Write Off", "Transfer"]
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	_DOCTYPE_NAME = "GL Entry"
