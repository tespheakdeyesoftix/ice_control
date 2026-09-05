# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from ice_control.api.accounting import get_account_type, submit_general_ledger_entry


VOUCHER_TYPE = "Expense Payment"


def delete_gl_entries(self):
	frappe.db.sql(
		"""
			delete from `tabGL Entry`
			where voucher_type = %(voucher_type)s
				and voucher_no = %(voucher_no)s
		""",
		{"voucher_type": VOUCHER_TYPE, "voucher_no": self.name},
	)


def submit_to_gl_entry(self):
	delete_gl_entries(self)

	payment_amount = flt(self.total_payment)
	write_off_amount = flt(self.total_write_off)
	if payment_amount <= 0 and write_off_amount <= 0:
		return

	
	payable_account = self.payable_account
	payment_account = self.account_code
	write_off_account = self.write_off_account

	expense_rows = [
		row
		for row in self.expenses
		if row.expense
		and (flt(row.payment_amount) > 0 or flt(row.write_off_amount) > 0)
	]
	expense_names = ", ".join(row.expense for row in expense_rows)
	base_entry = {
		"outlet": self.outlet,
		"posting_date": self.posting_date,
		"voucher_type": VOUCHER_TYPE,
		"voucher_no": self.name,
		"reference_doctype": VOUCHER_TYPE,
		"reference_docname": self.name,
		"remark": _("ទូទាត់ទៅ {0}. លេខចំណាយ: {1}").format(
			self.vendor_name or self.vendor,
			expense_names,
		),
	}
	entries = []

	if payment_amount > 0:
		entries.extend(
			[
				{
					**base_entry,
					"transaction_type": "Payment",
					"account": payable_account,
					"account_type": get_account_type(payable_account),
					"amount": payment_amount,
					"against": payment_account,
					"party_type": "Vendor",
					"party": self.vendor,
					"party_name": self.vendor_name,
				},
				{
					**base_entry,
					"transaction_type": "Payment",
					"account": payment_account,
					"account_type": get_account_type(payment_account),
					"amount": payment_amount,
					"against": payable_account,
				},
			]
		)

	if write_off_amount > 0:
		write_off_rows = [row for row in expense_rows if flt(row.write_off_amount) > 0]
		write_off_remark = _("កាត់ចោលចំណាយ: {0}").format(
			", ".join(
				f"{row.expense}: "
				f"{frappe.format(flt(row.write_off_amount), {'fieldtype': 'Currency'})}"
				for row in write_off_rows
			)
		)
		entries.extend(
			[
				
				{
					**base_entry,
					"transaction_type": "Write Off",
					"account": write_off_account,
					"account_type": get_account_type(write_off_account),
					"amount": write_off_amount,
					"against": payable_account,
					"remark": write_off_remark,
				}
			]
		)

	submit_general_ledger_entry(entries, run_commit=False)
