# Copyright (c) 2025, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from ice_control.api.inventory import add_inventory_transaction,get_stock_location_prouct
import json
from typing import Any
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
		for p in self.purchase_products:
			p.sub_total = p.quantity * p.cost
			p.total_cost = p.sub_total
		self.update_party_name()
		self.total_quantity = sum([d.quantity for d in self.purchase_products])
		self.total_cost = sum([d.total_cost for d in self.purchase_products])
		self.total_payment = sum([d.payment_amount for d in self.payments])
		self.write_off = sum([d.write_off_amount*(d.exchange_rate or 1) for d in self.payments])
		self.balance = (self.total_cost or 0) - (self.total_payment or 0) - (self.write_off or 0)
		if self.balance<0:
			frappe.throw(_("Payment amount cannot greater than purchase order amount"))
		update_status(self)

	def before_submit(self):
		self.validate_product_unit()

	def on_submit(self):
		add_payment(self.name)
		update_stock_product(self)
		update_status(self)
	
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

	def validate_product_unit(self):
		for p in [d for d in self.purchase_products if d.is_inventory_product ==1 and d.base_unit != d.unit]:
			sql="select name,multiplier from `tabProduct Units` where parent=%(product_code)s and unit = %(unit)s"
			data = frappe.db.sql(sql,{"product_code": p.product_code,"unit":p.unit},as_dict = 1)
			if data:
				p.multiplier = data[0].get("multiplier")
			else:
				frappe.throw("Product <strong>{}-{}</strong> does not have unit <strong>{}</strong>.".format(p.product_code,p.product_name,p.unit))

	def update_party_name(self):
		doctype = self.party_type
		name = self.party
		party_name =  frappe.get_value(doctype, name, '{}_name'.format(doctype.lower()))
		self.party_name = party_name
		if self.party_type in ["Customer","Vendor"]:
			self.phone_number = frappe.get_cached_value(self.party_type, self.party,"phone_number_1")
		else:
			self.phone_number = frappe.get_cached_value(self.party_type, self.party,"phone_number")

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

@frappe.whitelist()
def get_purchase_cost(param: dict[str, Any]) -> Any:
	doc = param.get("doc")
	product = param.get("product")
	vendor_price = frappe.db.sql("""select 
										cost 
									from `tabVendor Product Price` 
									where product = %(product_code)s and 
									stock_location = %(stock_location)s and
									unit = %(unit)s and
									parent = %(party)s""",{"product_code":product.get("product_code"),"stock_location":doc.get("stock_location"),"unit":product.get("unit"),"party":doc.get("party")},as_dict=1)
	if vendor_price:
		return vendor_price[0]["cost"]
	else:
		stock_location_product = frappe.db.sql("""select 
											cost 
										from `tabStock Location Products` 
										where product_code = %(product_code)s and 
										stock_location = %(stock_location)s and 
										unit = %(unit)s""",{"product_code":product.get("product_code"),"stock_location":doc.get("stock_location"),"unit":product.get("unit")},as_dict=1)
		if stock_location_product:
			return stock_location_product[0]["cost"]
		else:
			return frappe.db.get_value("Product",product_code,"cost")
			
def update_stock_product(self):
	data = [
		{
			"ref_doctype":self.doctype,
			"ref_docname":self.name,
			"posting_date":self.posting_date,
			"stock_location":self.stock_location,
			"product_code":p.product_code,
			"unit":p.unit,
			"quantity": p.quantity,
			"multiplier":p.multiplier or 1,
			"cost":p.cost,
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



	