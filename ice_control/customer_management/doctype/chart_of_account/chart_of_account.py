# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ChartofAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_code: DF.Data | None
		account_name: DF.Data | None
		account_name_kh: DF.Data | None
		account_type: DF.Literal["", "Receivable", "Payable", "Cash", "Bank", "Income", "Expense", "Temporary", "Stock Asset", "Fixed Asset"]
		is_group: DF.Check
		left: DF.Int
		old_parent: DF.Link | None
		parent_chart_of_account: DF.Link | None
		right: DF.Int
		root_type: DF.Literal["", "Asset", "Liabilities", "Equity", "Income", "Expenses"]
	# end: auto-generated types

	_DOCTYPE_NAME = "Chart of Account"
