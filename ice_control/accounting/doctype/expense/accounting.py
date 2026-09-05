# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from ice_control.api.accounting import get_account_type, submit_general_ledger_entry


VOUCHER_TYPE = "Expense"


def delete_gl_entries(self):
	frappe.db.sql(
		"""
			DELETE FROM `tabGL Entry`
			WHERE voucher_type = %(voucher_type)s
				AND voucher_no = %(voucher_no)s
		""",
		{"voucher_type": VOUCHER_TYPE, "voucher_no": self.name},
	)


def submit_to_gl_entry(self):
	delete_gl_entries(self)

	amounts_by_account = {}
	for row in self.expense_items:
		amount = flt(row.total_amount)
		if amount <= 0:
			continue
		if not row.expense_code:
			frappe.throw(
				_("Expense Account is required in row {0}.").format(row.idx)
			)
		amounts_by_account[row.expense_code] = (
			amounts_by_account.get(row.expense_code, 0) + amount
		)

	if not amounts_by_account:
		return

	payable_account = self.default_payable_account
	if not payable_account:
		frappe.throw(_("Default Payable Account is required."))
	if payable_account in amounts_by_account:
		frappe.throw(_("Payable Account and Expense Accounts must be different."))

	total_expense = sum(amounts_by_account.values())
	vendor_name = frappe.get_cached_value("Vendor", self.vendor, "vendor_name")
	expense_accounts = ", ".join(amounts_by_account)
	remark = self.note or _("Expense from {0}.").format(vendor_name or self.vendor)
	base_entry = {
		"outlet": self.outlet,
		"posting_date": self.posting_date,
		"voucher_type": VOUCHER_TYPE,
		"voucher_no": self.name,
		"reference_doctype": VOUCHER_TYPE,
		"reference_docname": self.name,
		"remark": remark,
	}

	entries = [
		{
			**base_entry,
			"account": account,
			"account_type": get_account_type(account),
			"debit_amount": amount,
			"against": payable_account,
		}
		for account, amount in amounts_by_account.items()
	]
	entries.append(
		{
			**base_entry,
			"account": payable_account,
			"account_type": get_account_type(payable_account),
			"credit_amount": total_expense,
			"against": expense_accounts,
			"party_type": "Vendor",
			"party": self.vendor,
			"party_name": vendor_name,
		}
	)

	submit_general_ledger_entry(entries, run_commit=False)
