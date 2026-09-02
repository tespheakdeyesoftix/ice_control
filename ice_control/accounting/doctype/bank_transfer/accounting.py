import frappe
from frappe import _
from frappe.utils import flt

from ice_control.api.accounting import get_account_type, submit_general_ledger_entry


def delete_gl_entries(self):
	frappe.db.sql(
		"""
		DELETE FROM `tabGL Entry`
		WHERE voucher_type = 'Bank Transfer'
			AND voucher_no = %(voucher_no)s
		""",
		{"voucher_no": self.name},
	)


def submit_to_gl_entry(self):
	delete_gl_entries(self)

	amount = flt(self.amount)
	transfer_from_remark = _("ផ្ទេរប្រាក់ពី {0} to {1}.").format(
		self.transfer_from,
		self.transfer_to,
	)
	transfer_to_remark = _("ផ្ទេរប្រាក់ទៅ {0} from {1}.").format(
		self.transfer_to,
		self.transfer_from,
	)
	if self.note:
		transfer_from_remark = f"{transfer_from_remark} {self.note}"
		transfer_to_remark = f"{transfer_to_remark} {self.note}"

	base_entry = {
		"outlet": self.outlet,
		"posting_date": self.posting_date,
		"voucher_type": "Bank Transfer",
		"voucher_no": self.name,
		"reference_doctype": "Bank Transfer",
		"reference_docname": self.name,
		"transaction_type": "Transfer",
	}
	entries = [
		{
			**base_entry,
			"account": self.transfer_from,
			"account_type": get_account_type(self.transfer_from),
			"credit_amount": amount,
			"against": self.transfer_to,
			"remark": transfer_from_remark,
		},
		{
			**base_entry,
			"account": self.transfer_to,
			"account_type": get_account_type(self.transfer_to),
			"debit_amount": amount,
			"against": self.transfer_from,
			"remark": transfer_to_remark,
		},
	]

	submit_general_ledger_entry(entries, run_commit=False)
