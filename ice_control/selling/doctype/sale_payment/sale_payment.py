# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt
from ice_control.api.utils import get_default_outlet,money_to_word,get_exchange_rate,get_current_employee_outlets
from ice_control.api.accounting import get_customer_credit_balance as _get_customer_credit_balance


class SalePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.sale_payment_invoices.sale_payment_invoices import SalePaymentInvoices

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

	def on_submit():
		if self.amount_to_pay < self.payment_amount:
			frappe.throw("ទឹកប្រាក់បង់មិនអាចធំជាងទឹកប្រាក់ត្រូវបង់ទេ")
			
		self.validate_sale_invoices()


	def validate_sale_invoices(self):
		for s in self.sales:
			sale_doc = frappe.get_doc("Sale",s.sale)
			# if doc.

	# custome doctype method

	@frappe.whitelist(methods=["POST"])
	def update_summary(self):
		sales = [x for x in self.sales if x.get("sale")] or []
		self.total_sales_invoice = len(sales)
		self.amount_to_pay = sum([x.get("sale_balance") or 0 for x in sales])
		self.payment_amount = flt(self.input_amount) / (flt(self.exchange_rate) or 1)
		self.payment_amount_in_word =money_to_word(self.payment_amount or 0)
		self.write_off_amount = sum([x.get("write_off_amount") or 0 for x in sales])
		self.balance =  sum([x.get("balance") or 0 for x in sales])

	@frappe.whitelist(methods=["POST"])
	def allocate_payment_amount(self):
		exchange_rate = flt(self.exchange_rate) or 1
		payment_to_allocate = max(flt(self.input_amount) / exchange_rate, 0)

		for sale in self.sales:
			sale_balance = max(flt(sale.sale_balance), 0)
			allocated_amount = min(payment_to_allocate, sale_balance) if sale.sale else 0

			sale.payment_amount = allocated_amount
			sale.balance = sale_balance - allocated_amount
			payment_to_allocate = max(payment_to_allocate - allocated_amount, 0)

		self.update_summary()


	@frappe.whitelist(methods=["POST"])
	def get_customer_credit_balance(self):
		self.customer_balance = _get_customer_credit_balance(customer = self.customer,date=self.posting_date, outlet = self.outlet)

	@frappe.whitelist(methods=["POST"])
	def get_exchange_rate(self):
		self.exchange_rate = get_exchange_rate(from_currency = frappe.get_cached_value("Business Information",None,"default_currency"), to_currency =self.currency)



def get_permission_query_conditions(user=None):
    user = user or frappe.session.user

    if user == "Administrator":
        return None

    access_outlets = get_current_employee_outlets()

    if not access_outlets:
        return "1 = 0"

    outlets = ", ".join(frappe.db.escape(outlet) for outlet in access_outlets)

    return f"`tabSale Payment`.`outlet` IN ({outlets})"
