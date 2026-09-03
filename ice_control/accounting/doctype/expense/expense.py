# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Expense(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.accounting.doctype.expense_items.expense_items import ExpenseItems

		expense_by_employee: DF.Link
		expense_items: DF.Table[ExpenseItems]
		naming_series: DF.Literal["EXP.YYYY.-.####"]
		outlet: DF.Link
		posting_date: DF.Date
		total_expense: DF.Currency
		vendor: DF.Link
	# end: auto-generated types

	_DOCTYPE_NAME = "Expense"

	def validate(self):
		for d in self.expense_items:
			d.total_amount = (d.price or 0) * (d.quantity or 0) 

		self.total_expense = sum([d.total_amount for d in self.expense_items])