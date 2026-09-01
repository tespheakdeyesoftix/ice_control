# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import escape_html, flt, fmt_money, formatdate
from ice_control.api.utils import get_default_outlet,money_to_word,get_exchange_rate,get_current_employee_outlets
from ice_control.api.accounting import get_customer_credit_balance as _get_customer_credit_balance
from ice_control.selling.doctype.sale_payment.accounting import submit_to_gl_entry


class SalePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.sale_payment_invoices.sale_payment_invoices import SalePaymentInvoices

		account_code: DF.Link | None
		amended_from: DF.Link | None
		amount_to_pay: DF.Currency
		balance: DF.Currency
		balance_virtual: DF.Currency
		created_by: DF.Data | None
		currency: DF.Link | None
		customer: DF.Link
		customer_balance: DF.Currency
		customer_name: DF.Data | None
		enable_multiple_payment_type: DF.Check
		exchange_rate: DF.Data | None
		input_amount: DF.Float
		naming_series: DF.Literal["SP.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		payment_amount: DF.Currency
		payment_amount_in_word: DF.Data | None
		payment_type: DF.Link | None
		photo: DF.AttachImage | None
		pos_sale_payment: DF.Data | None
		posting_date: DF.Date
		sale: DF.Link | None
		sales: DF.Table[SalePaymentInvoices]
		total_sales_invoice: DF.Int
		write_off_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Sale Payment"


	def validate(self):
		if self.is_new():
			self.created_by = frappe.get_cached_value("User",frappe.session.user,"full_name")

	def before_submit(self):
		self.validate_sale_invoices()

		if self.amount_to_pay < self.payment_amount:
			frappe.throw("ទឹកប្រាក់បង់មិនអាចធំជាងទឹកប្រាក់ត្រូវបង់ទេ")
		# validate account_code
		payment_type_doc = frappe.get_cached_doc("Payment Type", self.payment_type)
		default_account_record = next((x for x in payment_type_doc.default_account if x.get("outlet") == self.outlet), None)
		if default_account_record:
			self.account_code = default_account_record.default_sale_payment_account
		else:
			frappe.throw("សូមជ្រើសរើសលេខកូដគនណី")
			
	def on_submit(self):
		submit_to_gl_entry(self)

		if frappe.conf.get("developer_mode"):
			self.update_sale_payment_status()
			self.add_payment_info_comment_to_sale()
		else:
			frappe.enqueue(
				"ice_control.selling.doctype.sale_payment.sale_payment.update_sale_payment_status",
				queue="short",
				enqueue_after_commit=True,
				sale_payment=self.name,
			)
			frappe.enqueue(
				"ice_control.selling.doctype.sale_payment.sale_payment.add_payment_info_comment_to_sale",
				queue="short",
				enqueue_after_commit=True,
				sale_payment=self.name,
			)

	def on_cancel(self):
		frappe.db.sql(
			"""
			DELETE FROM `tabGL Entry`
			WHERE voucher_type = 'Sale Payment'
				AND voucher_no = %(voucher_no)s
			""",
			{"voucher_no": self.name},
		)

		if frappe.conf.get("developer_mode"):
			self.update_sale_payment_status()
		else:
			frappe.enqueue(
				"ice_control.selling.doctype.sale_payment.sale_payment.update_sale_payment_status",
				queue="short",
				enqueue_after_commit=True,
				sale_payment=self.name,
			)

	def update_sale_payment_status(self):
		sale_names = list({row.sale for row in self.sales if row.sale})
		if not sale_names:
			return

		frappe.db.sql(
			"""
			UPDATE `tabSale` AS sale
			LEFT JOIN (
				SELECT
					invoice.sale,
					COALESCE(SUM(invoice.payment_amount), 0) AS total_payment,
					COALESCE(SUM(invoice.write_off_amount), 0) AS total_write_off
				FROM `tabSale Payment Invoices` AS invoice
				INNER JOIN `tabSale Payment` AS sale_payment
					ON sale_payment.name = invoice.parent
					AND sale_payment.docstatus = 1
				WHERE invoice.sale IN %(sale_names)s
				GROUP BY invoice.sale
			) AS totals ON totals.sale = sale.name
			SET
				sale.total_payment = COALESCE(totals.total_payment, 0),
				sale.total_write_off = COALESCE(totals.total_write_off, 0),
				sale.balance = GREATEST(
					sale.total_amount
					- COALESCE(totals.total_payment, 0)
					- COALESCE(totals.total_write_off, 0),
					0
				),
				sale.status = CASE
					WHEN sale.total_amount
						- COALESCE(totals.total_payment, 0)
						- COALESCE(totals.total_write_off, 0) <= 0
						THEN "Paid"
					WHEN COALESCE(totals.total_payment, 0) > 0
						THEN "Partially Paid"
					ELSE "Unpaid"
				END
			WHERE sale.name IN %(sale_names)s
			""",
			{"sale_names": tuple(sale_names)},
		)

		for sale_name in sale_names:
			frappe.clear_document_cache("Sale", sale_name)

	def add_payment_info_comment_to_sale(self):
		currency = frappe.get_cached_value(
			"Business Information", None, "default_currency"
		) or self.currency
		payment_date = formatdate(self.posting_date)
		received_by = escape_html(self.created_by or self.owner or frappe.session.user)
		note = escape_html(self.note) if self.note else None

		for row in self.sales:
			payment_amount = flt(row.payment_amount)
			write_off_amount = flt(row.write_off_amount)
			if not row.sale or (payment_amount <= 0 and write_off_amount <= 0):
				continue

			marker = f"sale-payment-receipt:{self.name}"
			if frappe.db.exists(
				"Comment",
				{
					"reference_doctype": "Sale",
					"reference_name": row.sale,
					"comment_type": "Comment",
					"content": ["like", f"%{marker}%"],
				},
			):
				continue

			content = _(
				"Payment received {0} on {1}. Write-off amount: {2}. Payment receipt number: {3}."
			).format(
				frappe.bold(fmt_money(payment_amount, currency=currency)),
				frappe.bold(payment_date),
				frappe.bold(fmt_money(write_off_amount, currency=currency)),
				frappe.bold(escape_html(self.name)),
			)
			if note:
				content += " " + _("Note: {0}.").format(note)
			content += " " + _("Received by: {0}.").format(frappe.bold(received_by))
			content += f"<!-- {marker} -->"

			frappe.get_doc("Sale", row.sale).add_comment("Comment", content)

	def validate_sale_invoices(self):
		valid_rows = []
		seen_sales = set()

		for row in self.sales:
			if not row.sale:
				frappe.throw(_("Row {0}: Sale Invoice is required.").format(row.idx))

			if row.sale in seen_sales:
				frappe.throw(
					_("Sale Invoice {0} is selected more than once.").format(
						frappe.bold(row.sale)
					)
				)
			seen_sales.add(row.sale)

			sale_doc = frappe.get_doc("Sale", row.sale)
			sale_balance = flt(sale_doc.balance)
			payment_amount = flt(row.payment_amount)
			write_off_amount = flt(row.write_off_amount)

			if sale_doc.sale_status != "Closed":
				frappe.throw(
					_("Sale Invoice {0} must be Closed.").format(frappe.bold(row.sale))
				)

			if sale_balance <= 0:
				frappe.throw(
					_("Sale Invoice {0} has no outstanding balance.").format(
						frappe.bold(row.sale)
					)
				)

			if payment_amount < 0 or write_off_amount < 0:
				frappe.throw(
					_("Row {0}: Payment Amount and Write-off Amount cannot be negative.").format(
						row.idx
					)
				)

			if payment_amount == 0 and write_off_amount == 0:
				continue

			allocated_amount = payment_amount + write_off_amount
			if allocated_amount - sale_balance > 0.000001:
				frappe.throw(
					_("Sale Invoice {0}: Payment Amount plus Write-off Amount cannot exceed the current balance of {1}.").format(
						frappe.bold(row.sale),
						frappe.format_value(sale_balance, {"fieldtype": "Currency"}),
					)
				)

			if write_off_amount > 0 and abs(allocated_amount - sale_balance) > 0.000001:
				frappe.throw(
					_("Sale Invoice {0}: A write-off must fully settle the current balance of {1}.").format(
						frappe.bold(row.sale),
						frappe.format_value(sale_balance, {"fieldtype": "Currency"}),
					)
				)

			row.sale_balance = sale_balance
			row.balance = sale_balance - allocated_amount
			valid_rows.append(row)

		if not valid_rows:
			frappe.throw(
				_("Please enter a Payment Amount or Write-off Amount for at least one Sale Invoice.")
			)

		self.set("sales", valid_rows)
		self.update_summary()

	# custome doctype method

	@frappe.whitelist(methods=["POST"])
	def update_summary(self):
		sales = [x for x in self.sales if x.get("sale")] or []
		self.total_sales_invoice = len(sales)
		self.amount_to_pay = sum([x.get("sale_balance") or 0 for x in sales])
		self.payment_amount = sum([flt(x.get("payment_amount")) for x in sales])
		self.payment_amount_in_word =money_to_word(self.payment_amount or 0)
		self.write_off_amount = sum([x.get("write_off_amount") or 0 for x in sales])
		self.balance =  sum([x.get("balance") or 0 for x in sales])

	@frappe.whitelist(methods=["POST"])
	def allocate_payment_amount(self):
		exchange_rate = flt(self.exchange_rate) or 1
		payment_to_allocate = max(flt(self.input_amount) / exchange_rate, 0)

		for sale in self.sales:
			sale_balance = max(flt(sale.sale_balance), 0)
			write_off_amount = min(
				max(flt(sale.write_off_amount), 0), sale_balance
			)
			amount_after_write_off = sale_balance - write_off_amount
			allocated_amount = (
				min(payment_to_allocate, amount_after_write_off) if sale.sale else 0
			)

			sale.write_off_amount = write_off_amount
			sale.payment_amount = allocated_amount
			sale.balance = amount_after_write_off - allocated_amount
			payment_to_allocate = max(payment_to_allocate - allocated_amount, 0)

		self.update_summary()


	@frappe.whitelist(methods=["POST"])
	def get_customer_credit_balance(self):
		self.customer_balance = _get_customer_credit_balance(customer = self.customer,date=self.posting_date, outlet = self.outlet)

	@frappe.whitelist(methods=["POST"])
	def get_exchange_rate(self):
		self.exchange_rate = get_exchange_rate(from_currency = frappe.get_cached_value("Business Information",None,"default_currency"), to_currency =self.currency)




def update_sale_payment_status(sale_payment: str):
	doc = frappe.get_doc("Sale Payment", sale_payment)
	doc.update_sale_payment_status()


def add_payment_info_comment_to_sale(sale_payment: str):
	doc = frappe.get_doc("Sale Payment", sale_payment)
	if doc.docstatus == 1:
		doc.add_payment_info_comment_to_sale()



def get_permission_query_conditions(user=None):
    user = user or frappe.session.user

    if user == "Administrator":
        return None

    access_outlets = get_current_employee_outlets()

    if not access_outlets:
        return "1 = 0"

    outlets = ", ".join(frappe.db.escape(outlet) for outlet in access_outlets)

    return f"`tabSale Payment`.`outlet` IN ({outlets})"
