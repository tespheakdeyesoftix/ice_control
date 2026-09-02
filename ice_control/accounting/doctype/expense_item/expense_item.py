# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ExpenseItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		expense_item_code: DF.Data
		expense_item_name: DF.Data
		price: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Expense Item"
