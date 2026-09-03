import frappe
from frappe import _
from frappe.utils import flt

from ice_control.api.accounting import get_account_type, submit_general_ledger_entry


VOUCHER_TYPE = "Purchase Order Payment"


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

	payment_amount = flt(self.payment_amount)
	write_off_amount = flt(self.total_write_off_amount)
	if payment_amount <= 0 and write_off_amount <= 0:
		return

	outlet = frappe.get_cached_doc("Outlet", self.outlet)
	payable_account = outlet.default_payable_account
	payment_account = self.payment_from_account
	write_off_account = outlet.default_purchase_write_off_account

	if not payable_account:
		frappe.throw(
			_("Please set Default Payable Account for Outlet {0}.").format(
				frappe.bold(self.outlet)
			)
		)

	if payment_amount > 0:
		if not payment_account:
			frappe.throw(_("Payment from Account is required."))
		if payment_account == payable_account:
			frappe.throw(
				_("Payment from Account and Payable Account must be different.")
			)

	if write_off_amount > 0:
		if not write_off_account:
			frappe.throw(
				_("Please set Default Purchase Write Off Account for Outlet {0}.").format(
					frappe.bold(self.outlet)
				)
			)
		if write_off_account == payable_account:
			frappe.throw(
				_("Purchase Write Off Account and Payable Account must be different.")
			)

	purchase_order_rows = [
		row
		for row in self.purchase_orders
		if row.purchase_order
		and (flt(row.payment_amount) > 0 or flt(row.write_off_amount) > 0)
	]
	purchase_order_names = ", ".join(row.purchase_order for row in purchase_order_rows)
	base_entry = {
		"outlet": self.outlet,
		"posting_date": self.posting_date,
		"voucher_type": VOUCHER_TYPE,
		"voucher_no": self.name,
		"reference_doctype": VOUCHER_TYPE,
		"reference_docname": self.name,
		"remark": self.note
		or _("Payment to {0}. Purchase Orders: {1}").format(
			self.party_name or self.party,
			purchase_order_names,
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
					"debit_amount": payment_amount,
					"against": payment_account,
					"party_type": self.party_type,
					"party": self.party,
					"party_name": self.party_name,
				},
				{
					**base_entry,
					"transaction_type": "Payment",
					"account": payment_account,
					"account_type": get_account_type(payment_account),
					"credit_amount": payment_amount,
					"against": payable_account,
				},
			]
		)

	if write_off_amount > 0:
		write_off_rows = [row for row in purchase_order_rows if flt(row.write_off_amount) > 0]
		write_off_remark = _("Write off Purchase Orders: {0}").format(
			", ".join(
				f"{row.purchase_order}: "
				f"{frappe.format(flt(row.write_off_amount), {'fieldtype': 'Currency'})}"
				for row in write_off_rows
			)
		)
		entries.extend(
			[
				{
					**base_entry,
					"transaction_type": "Write Off",
					"account": payable_account,
					"account_type": get_account_type(payable_account),
					"debit_amount": write_off_amount,
					"against": write_off_account,
					"party_type": self.party_type,
					"party": self.party,
					"party_name": self.party_name,
					"remark": write_off_remark,
				},
				{
					**base_entry,
					"transaction_type": "Write Off",
					"account": write_off_account,
					"account_type": get_account_type(write_off_account),
					"credit_amount": write_off_amount,
					"against": payable_account,
					"remark": write_off_remark,
				},
			]
		)

	submit_general_ledger_entry(entries, run_commit=False)

