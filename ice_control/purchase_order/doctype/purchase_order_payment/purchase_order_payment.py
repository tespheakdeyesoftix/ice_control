# Copyright (c) 2025, Tes Pheakdey and contributors
# For license information, please see license.txt

from frappe import _
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from ice_control.api.accounting import (
	get_party_account_payable_balance as _get_party_account_payable_balance,
)
from ice_control.api.api import money_to_word
from ice_control.api.utils import validate_close_date
from ice_control.purchase_order.doctype.purchase_order_payment.accounting import (
	delete_gl_entries,
	submit_to_gl_entry,
)


class PurchaseOrderPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.purchase_order.doctype.purchase_order_payment_invoices.purchase_order_payment_invoices import PurchaseOrderPaymentInvoices

		account_paid_from: DF.Link | None
		account_paid_to: DF.Link | None
		amended_from: DF.Link | None
		amount_to_pay: DF.Currency
		balance: DF.Currency
		created_by: DF.Data | None
		currency: DF.Link | None
		default_write_off_account: DF.Link | None
		exchange_rate: DF.Data | None
		from_purchase_orders: DF.Check
		input_amount: DF.Float
		naming_series: DF.Literal["POP.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link
		party: DF.DynamicLink
		party_name: DF.Data | None
		party_payable_balance: DF.Currency
		party_type: DF.Literal["Vendor", "Employee", "Customer"]
		payment_amount: DF.Currency
		payment_amount_in_word: DF.Data | None
		payment_type: DF.Link
		photo: DF.AttachImage | None
		posting_date: DF.Date
		purchase_orders: DF.Table[PurchaseOrderPaymentInvoices]
		reference_number: DF.Data | None
		total_invoices: DF.Int
		total_write_off_amount: DF.Currency
	# end: auto-generated types

	def validate(self):
		if self.is_new():
			self.created_by  = frappe.get_cached_value("User",frappe.session.user,"full_name")
		validate_payment_amount(self)
		validate_accounts(self)
		validate_close_date(self.posting_date, self.creation, self.outlet)
		self.payment_amount_in_word = money_to_word(int(self.payment_amount))
		self.validate_purchase_order_payment_invoices()
		update_totals(self)
		

	def before_submit(self):
		self.purchase_orders = [d for d in self.purchase_orders if (d.payment_amount or 0)>0  or (d.write_off_amount or 0)>0]
		# update to amount to pay
		self.amount_to_pay = sum([d.get("purchase_order_balance") or 0 for d in self.purchase_orders])

	def on_submit(self):
		if self.from_purchase_orders == 0:
			update_purchase_order(self.name)
			submit_to_gl_entry(self)

	def on_cancel(self):
		self.flags.ignore_links = True
		delete_gl_entries(self)
		update_purchase_order(self.name)

	def validate_purchase_order_payment_invoices(self):
		if (self.from_purchase_orders or 0) == 0:
			for s in self.purchase_orders:
				s.payment_date = self.posting_date
				s.party_type = self.party_type
				s.party = self.party
				s.purchase_order_balance = frappe.db.get_value("Purchase Orders",s.purchase_order,["balance"])
				s.balance = (s.purchase_order_balance or 0) - ((s.payment_amount or 0) + (s.write_off_amount or 0))
				s.payment_type = self.payment_type

	@frappe.whitelist(methods=["POST"])
	def allocate_payment_amount(self):
		exchange_rate = flt(self.exchange_rate) or 1
		payment_to_allocate = max(flt(self.input_amount) / exchange_rate, 0)

		for purchase_order in self.purchase_orders:
			purchase_order_balance = max(flt(purchase_order.purchase_order_balance), 0)
			write_off_amount = min(
				max(flt(purchase_order.write_off_amount), 0),
				purchase_order_balance,
			)
			amount_after_write_off = purchase_order_balance - write_off_amount
			allocated_amount = (
				min(payment_to_allocate, amount_after_write_off)
				if purchase_order.purchase_order
				else 0
			)

			purchase_order.exchange_rate = exchange_rate
			purchase_order.payment_amount = allocated_amount
			purchase_order.write_off_amount = write_off_amount
			purchase_order.balance = amount_after_write_off - allocated_amount
			payment_to_allocate = max(payment_to_allocate - allocated_amount, 0)

		update_totals(self)

	@frappe.whitelist(methods=["POST"])
	def update_summary(self):
		update_totals(self)

	@frappe.whitelist(methods=["POST"])
	def get_party_account_payable_balance(self):
		self.party_payable_balance = _get_party_account_payable_balance(
			party_type=self.party_type,
			party=self.party,
			outlet=self.outlet,
			date=self.posting_date,
		)

	@frappe.whitelist()
	def get_unpaid_purchase_orders(self):
		data = []
		sql = """select 
					outlet,
					party_type,
					party,
					party_name,
					name, 
					posting_date, 
					total_cost,
					total_payment,
					balance 
				from `tabPurchase Orders` 
				where  1= 1
					and (name = %(purchase_order)s or %(purchase_order)s = '')  
					and balance> 0
					and docstatus = 1
					and party=%(party)s 
					and outlet = %(outlet)s  
					{}
				order by 
					posting_date,
					name
			"""
		filter = {
			"outlet":self.outlet,
			"purchase_order":self.purchase_orders or '',
			"party": self.party
		}

		if self.start_date and self.end_date:
			sql = sql.format("and (posting_date between %(start_date)s and %(end_date)s)") 
			filter.update({
				"start_date":self.start_date, 
				"end_date":self.end_date
			})
		else:
			sql = sql.format("and 1=1")
		data = frappe.db.sql(sql, filter,as_dict = 1)
		return data or []
		
def update_totals(self):
	purchase_orders = [row for row in self.purchase_orders if row.purchase_order]
	self.total_write_off_amount = sum(flt(row.write_off_amount) for row in purchase_orders)
	self.amount_to_pay = sum(flt(row.purchase_order_balance) for row in purchase_orders)
	self.total_invoices = len(purchase_orders)
	self.payment_amount = sum(flt(row.payment_amount) for row in purchase_orders)
	self.balance = self.amount_to_pay - (self.payment_amount + self.total_write_off_amount)
	self.payment_amount_in_word = money_to_word(int(self.payment_amount or 0))

def update_purchase_order(name):
	frappe.db.sql(
		"""
			with a as (
				select 
					p.purchase_order,	
					COALESCE(SUM(p.payment_amount), 0) AS total_payment,
					COALESCE(SUM(p.write_off_amount), 0) AS write_off_amount 

			)
			update `tabPurchase Order` 
		""",
		{"payment_name": name},
	)
	update_status(name)

def update_status(name):
	doc = frappe.get_doc("Purchase Orders", name)
	status = ""
	if doc.docstatus == 0:
		status = "Draft"
	elif doc.docstatus == 1:
		if doc.balance == 0:
			status = "Paid"
		elif doc.balance > 0 and doc.balance < doc.total_cost:
			status = "Partially Paid"
		else:
			status = "Unpaid"
	elif doc.docstatus == 2:
		status = "Cancelled"
	frappe.db.set_value("Purchase Orders", name, "status", status, update_modified=False)

def validate_payment_amount(self):
	if self.balance<0:
		frappe.throw(_("ទឹកប្រាក់ទូទាត់មិនអាចធំជាងទឹកប្រាក់ត្រូវបង់បានទេ"))

def validate_accounts(self):
	from ice_control.api.api import get_outlet_default_accounts,get_payment_type_default_account
	payment_type = get_payment_type_default_account(self.payment_type,self.outlet)
	outlet = get_outlet_default_accounts(self.outlet)
	self.account_paid_from = self.account_paid_from or payment_type.get("default_account")
	self.account_paid_to = self.account_paid_to or outlet.get("default_payable_account")
	self.default_write_off_account = self.default_write_off_account or outlet.get("default_purchase_write_off_account")

	if not self.account_paid_from:
		frappe.throw(_("Please select account paid from"))
	if not self.account_paid_to:
		frappe.throw(_("Please select account paid to"))
	if not self.default_write_off_account:
		frappe.throw(_("Please select default write off account"))

	account_field = ["account_paid_from","account_paid_to","default_write_off_account"]
	accounts = []
	for a in account_field:
		if self.get(a) in accounts:
			frappe.throw(_("<b>Account {0}</b> Is Already Selected.").format(self.get(a)))
		else:
			accounts.append(self.get(a))