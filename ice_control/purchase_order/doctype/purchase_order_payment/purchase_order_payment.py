# Copyright (c) 2025, Tes Pheakdey and contributors
# For license information, please see license.txt

from frappe import _
import frappe
from frappe.model.document import Document
from ice_control.api.api import money_to_word


class PurchaseOrderPayment(Document):
	def validate(self):
		self.payment_amount_in_word = money_to_word(int(self.payment_amount))
		self.validate_purchase_order_payment_invoices()
		update_totals(self)
		self.validate_payment_amount()

	def before_submit(self):
		self.purchase_orders = [d for d in self.purchase_orders if (d.payment_amount or 0)>0  or (d.write_off_amount or 0)>0]

	def on_submit(self):
		if self.from_purchase_orders == 0:
			update_purchase_order(self.name)

	def on_cancel(self):
		self.flags.ignore_links = True
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
	
	def validate_payment_amount(self):
		if self.balance<0:
			frappe.throw(_("Payment amount cannot greater than amount to pay"))
	
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
	self.total_write_off_amount = sum(float(a.write_off_amount or 0) for a in self.purchase_orders)
	self.amount_to_pay = sum(float(a.purchase_order_balance or 0) for a in self.purchase_orders)
	self.total_invoice = len([d  for d in self.purchase_orders if (d.payment_amount or 0)> 0 or (d.write_off_amount or 0)>0 ])
	self.payment_amount = sum([d.payment_amount or 0 for d in self.purchase_orders if (d.payment_amount or 0)> 0 ])
	self.balance = self.amount_to_pay - (self.payment_amount + self.total_write_off_amount)

def update_purchase_order(name):
	doc = frappe.get_doc("Purchase Order Payment",name)
	if doc.docstatus == 1:
		for p in doc.purchase_orders:
			write_off,total_payment,balance = frappe.db.get_value("Purchase Orders",p.purchase_order,['write_off', 'total_payment','balance'])
			frappe.db.set_value("Purchase Orders",p.purchase_order,{
				'write_off': write_off + p.write_off_amount,
				'total_payment': total_payment + p.payment_amount,
				'balance' : balance - (p.payment_amount+p.write_off_amount)
			})
			update_status(p.purchase_order)
	elif doc.docstatus == 2:
		for p in doc.purchase_orders:
			write_off,total_payment,balance = frappe.db.get_value("Purchase Orders",p.purchase_order,['write_off', 'total_payment','balance'])
			frappe.db.set_value("Purchase Orders",p.purchase_order,{
				'write_off': write_off - p.write_off_amount,
				'total_payment': total_payment - (p.payment_amount),
				'balance' : balance + (p.payment_amount+p.write_off_amount)
			})
			if doc.from_purchase_orders == 1:
				input_amount,payment_amount,write_off_amount = frappe.db.get_value("Purchase Order Payment Child",doc.payment_name,['input_amount', 'payment_amount','write_off_amount'])
				frappe.db.set_value("Purchase Order Payment Child",doc.payment_name,{
				'input_amount': input_amount - doc.input_amount,
				'payment_amount': payment_amount - doc.payment_amount,
				'write_off_amount' : write_off_amount - doc.total_write_off_amount
			})
			update_status(p.purchase_order)

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