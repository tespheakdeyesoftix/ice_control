# Copyright (c) 2025, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from ice_control.api.inventory import add_inventory_transaction
import json
class PurchaseOrders(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.purchase_order.doctype.purchase_order_payment_child.purchase_order_payment_child import PurchaseOrderPaymentChild
		from ice_control.purchase_order.doctype.purchase_order_products.purchase_order_products import PurchaseOrderProducts

		amended_from: DF.Link | None
		balance: DF.Currency
		default_expense_account: DF.Link
		default_payable_account: DF.Link
		default_stock_account: DF.Link
		default_write_off_account: DF.Link
		employee: DF.Link | None
		employee_name: DF.Data | None
		naming_series: DF.Literal["PO.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link | None
		party: DF.DynamicLink
		party_name: DF.Data | None
		party_type: DF.Literal["Vendor", "Employee", "Customer"]
		payments: DF.Table[PurchaseOrderPaymentChild]
		phone_number: DF.Data | None
		photo: DF.AttachImage | None
		posting_date: DF.Date
		purchase_products: DF.Table[PurchaseOrderProducts]
		reference_number: DF.Data | None
		status: DF.Literal["Draft", "Submitted", "Unpaid", "Paid", "Partially Paid", "Cancelled"]
		stock_location: DF.Link
		total_cost: DF.Currency
		total_payment: DF.Currency
		total_quantity: DF.Float
		write_off: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_product_unit()
		validate_accounts(self)
		for p in self.purchase_products:
			p.sub_total = p.quantity * p.cost
			p.total_cost = p.sub_total
		self.update_party_name()
		self.total_quantity = sum([d.quantity for d in self.purchase_products])
		self.total_cost = sum([d.total_cost for d in self.purchase_products])
		self.total_payment = sum([d.payment_amount for d in self.payments])
		self.write_off = sum([float(d.write_off_amount or 0)*float(d.exchange_rate or 1) for d in self.payments])
		self.balance = (self.total_cost or 0) - (self.total_payment or 0) - (self.write_off or 0)
		if self.balance<0:
			frappe.throw(_("Payment amount cannot greater than purchase order amount"))
		update_status(self)

	def on_submit(self):
		add_payment(self.name)
		update_stock_product(self)
		update_status(self)
		submit_to_GL_entry(self)

	def on_cancel(self):
		update_status(self)
		data = [
			{
				"ref_doctype":self.doctype,
				"ref_docname":self.name,
				"posting_date":self.posting_date,
				"stock_location":self.stock_location,
				"product_code":p.product_code,
				"unit":p.unit,
				"quantity": -1 * p.quantity,
				"multiplier":p.multiplier or 1,
				"cost":p.cost,
				"note": "ដកចំនួនពីបញ្ជារទិញលេខ {}".format(self.name)
			}
			for p in self.purchase_products if p.is_inventory_product == 1
		]
		add_inventory_transaction(data)
		from ice_control.api.accounting import cancel_general_ledger_entery
		cancel_general_ledger_entery("Purchase Order", self.name)

	def validate_product_unit(self):
		from ice_control.api.inventory import get_purchase_cost
		for p in [d for d in self.purchase_products if d.is_inventory_product ==1 and d.base_unit != d.unit]:
			data = get_purchase_cost(param={"doc": self,"product": p})
			if data:
				p.cost = float(data.get("cost"))
				p.multiplier = float(data.get("multiplier"))

	def update_party_name(self):
		doctype = self.party_type
		name = self.party
		party_name =  frappe.get_value(doctype, name, '{}_name'.format(doctype.lower()))
		self.party_name = party_name
		if self.party_type in ["Customer","Vendor"]:
			self.phone_number = frappe.get_cached_value(self.party_type, self.party,"phone_number_1")
		else:
			self.phone_number = frappe.get_cached_value(self.party_type, self.party,"phone_number")

	@frappe.whitelist()
	def get_payment_history(self):
		return frappe.db.sql(
			"""
			SELECT
				p.name AS payment_number,
				p.posting_date AS payment_date,
				i.payment_amount,
				i.write_off_amount,
				COALESCE(NULLIF(TRIM(p.created_by), ''), p.owner) AS created_by,
				p.creation
			FROM `tabPurchase Order Payment Invoices` i
			INNER JOIN `tabPurchase Order Payment` p
				ON p.name = i.parent
			WHERE i.purchase_order = %(purchase_order)s
				AND i.docstatus = 1
				AND p.docstatus = 1
			ORDER BY p.posting_date DESC, p.creation DESC
			""",
			{"purchase_order": self.name},
			as_dict=True,
		)

def update_status(self):
	status = ""
	if self.docstatus == 0:
		status = "Draft"
	elif self.docstatus == 1:
		if self.balance == 0:
			status = "Paid"
		elif self.balance > 0 and self.balance < self.total_cost:
			status = "Partially Paid"
		else:
			status = "Unpaid"
	elif self.docstatus == 2:
		status = "Cancelled"
	self.status = status

def validate_accounts(self):
	from ice_control.api.api import get_product_default_account,get_payment_type_default_account
	for a in self.purchase_products:
		if not a.default_stock_account:
			a.default_stock_account = get_product_default_account(a.product_code, self.outlet).get("default_stock_account")
		if not a.default_expense_account:
			a.default_expense_account = get_product_default_account(a.product_code, self.outlet).get("default_expense_account")
	for a in self.payments:
		if not a.default_account:
			a.default_account = get_payment_type_default_account(a.payment_type, self.outlet).get("default_account")
			
def update_stock_product(self):
	data = [
		{
			"ref_doctype":self.doctype,
			"ref_docname":self.name,
			"posting_date":self.posting_date,
			"stock_location":self.stock_location,
			"product_code":p.product_code,
			"unit": p.unit,
			"quantity": p.quantity,
			"multiplier": p.multiplier or 1,
			"cost": p.cost,
			"note": "បញ្ជូលចំនួនបន្ថែមពីបញ្ជារទិញលេខ {}".format(self.name)
		}
		for p in self.purchase_products if p.is_inventory_product == 1
	]
	add_inventory_transaction(data)

def add_payment(name):
	total_payment = 0
	write_off_amount = 0
	doc = frappe.get_doc("Purchase Orders",name)
	for a in doc.payments:
		p = frappe.new_doc("Purchase Order Payment")
		p.from_purchase_orders = 1
		p.posting_date = doc.posting_date
		p.outlet = doc.outlet
		p.payment_type = a.payment_type
		p.currency = a.currency
		p.exchange_rate = a.exchange_rate
		p.party_type = doc.party_type
		p.party = doc.party
		p.input_amount = a.input_amount
		p.payment_amount = a.payment_amount
		p.amount_to_pay = doc.total_cost
		purchase_order_balance = doc.total_cost - total_payment - write_off_amount
		total_payment += a.payment_amount
		write_off_amount += a.write_off_amount
		p.balance = doc.total_cost - total_payment - write_off_amount
		p.payment_name = a.name
		p.append("purchase_orders", {
			"purchase_order": doc.name,
			"party_type": doc.party_type,
			"party": doc.party,
			"outlet": doc.outlet,
			"payment_date": doc.posting_date,
			"exchange_rate": a.exchange_rate,
			"payment_type": a.payment_type,
			"posting_date": doc.posting_date,
			"purchase_order_balance": purchase_order_balance,
			"payment_amount": a.payment_amount,
			"write_off_amount": a.write_off_amount,
			"balance": p.balance
		})
		p.submit()

def submit_to_GL_entry(self):
	from ice_control.api.accounting import submit_general_ledger_entry
	docs = []
	for acc in set([d.default_stock_account for d in self.purchase_products]):
		if not acc:
				frappe.throw(_("Account code in purchase order product is required."))
		doc = {
			"doctype":"GL Entry",
			"outlet":self.outlet,
			"posting_date":self.posting_date,
			"account":acc,
			"debit_amount":sum([d.total_cost for d in self.purchase_products if d.default_stock_account == acc]),
			"against":self.party + " - " + self.party_name,
			"voucher_type":"Purchase Orders",
			"voucher_no":self.name,
			"remark":"បញ្ជាទិញពី {0} នៅថ្ងៃទី {1}។ សរុបទឹកប្រាក់ {2}".format(
				self.party + "-" + self.party_name ,
				frappe.format(self.posting_date,{"fieldtype":"Date"}),
				frappe.format(sum([d.total_cost for d in self.purchase_products if d.default_stock_account == acc]),{"fieldtype":"Currency"})),
			"party_type": self.party_type,
			"party": self.party,
			"party_name": self.party_name,
		}
		docs.append(doc)

	# add payment account
	for acc in set([d.default_account for d in self.payments]):
		if not acc:
				frappe.throw(_("Please enter payment account code in payment list"))
		doc = {
			"doctype":"GL Entry",
			"outlet":self.outlet,
			"posting_date":self.posting_date,
			"account":acc,
			"credit_amount":sum([d.payment_amount for d in self.payments if d.default_account == acc]),
			"against":self.name,
			"voucher_type":"Purchase Orders",
			"voucher_no":self.name,
			"remark":"ទូទាត់ទឹកប្រាក់បញ្ជាទិញអោយ {0}, នៅថ្ងៃទី {1}, ចំនួនទឹកប្រាក់​ {2}".format(
				self.party + "-" + self.party_name,
				frappe.format(self.posting_date,{"fieldtype":"Date"}),
				frappe.format(sum([d.payment_amount for d in self.payments if d.default_account == acc]),{"fieldtype":"Currency"})
			),
			"party_type":self.party_type,
			"party": self.party,
			"party_name": self.party_name
		}
		docs.append(doc)

	if self.write_off:
		if not self.default_write_off_account:
			frappe.throw(_('Please select write off account'))
		doc = {
			"doctype":"GL Entry",
			"outlet":self.outlet,
			"posting_date":self.posting_date,
			"account":self.default_write_off_account,
			"credit_amount":self.write_off,
			"against_voucher_type":"Purchase Orders",
			"against_voucher_no": self.name,
			"voucher_type":"Purchase Orders",
			"voucher_no":self.name,
			"party_type": self.party_type,
			"party":self.party,
			"party_name":self.party_name,
			"remark":"កាត់ចេញពីបញ្ជាទិញលេខ {0} នៅថ្ងៃទី {1}។ ចំនួនទឹកប្រាក់ {2}".format(
				self.name,
				frappe.format(self.posting_date,{"fieldtype":"Date"}),
				frappe.format(self.write_off or 0,{"fieldtype":"Currency"}))
		}
		docs.append(doc)

	if self.balance:
		if not self.default_payable_account:
			frappe.throw(_('Please select payable account'))
		doc = {
			"doctype":"GL Entry",
			"outlet":self.outlet,
			"posting_date":self.posting_date,
			"account":self.default_payable_account,
			"credit_amount":self.balance,
			"against_voucher_type":"Purchase Orders",
			"against_voucher_no": self.name,
			"voucher_type":"Purchase Orders",
			"voucher_no":self.name,
			"party_type": self.party_type,
			"party":self.party,
			"party_name":self.party_name,
			"remark":"បញ្ជាទិញពី {0} នៅថ្ងៃទី {1}។ សរុបទឹកប្រាក់ {2}។ ជំពាក់ {3}".format(
				self.party + "-" + self.party_name ,
				frappe.format(self.posting_date,{"fieldtype":"Date"}),
				frappe.format(sum([d.total_cost for d in self.purchase_products if d.default_stock_account == acc]),{"fieldtype":"Currency"}),
																				frappe.format(self.balance or 0,{"fieldtype":"Currency"})
																				),
		}
		docs.append(doc)
	submit_general_ledger_entry(docs=docs)
