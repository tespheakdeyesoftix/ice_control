# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
 
from frappe.model.document import Document
from frappe.utils.data import strip
import json
 
from frappe import _ 
from frappe.utils.caching import redis_cache
from ice_control.api.inventory import add_inventory_transaction



class Product(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.customer_management.doctype.product_outlet.product_outlet import ProductOutlet
		from ice_control.customer_management.doctype.product_units.product_units import ProductUnits

		allow_purchase: DF.Check
		allow_purchase_in_purchase_ice_feature: DF.Check
		allow_split_bill: DF.Check
		allow_sum_qty: DF.Check
		color: DF.Color | None
		cost: DF.Currency
		costing_method: DF.Literal["Average Cost", "Fixed Cost"]
		default_sale_stock_location: DF.Link | None
		default_sale_transaction_type: DF.Literal["", "Sale", "Borrow", "Sale", "Borrow"]
		enabled: DF.Check
		is_inventory_product: DF.Check
		multiplier: DF.Float
		opening_quantity: DF.Float
		photo: DF.AttachImage | None
		price: DF.Currency
		product_category: DF.Link
		product_code: DF.Data | None
		product_name: DF.Data
		product_outlet: DF.Table[ProductOutlet]
		product_outlets: DF.LongText | None
		product_units: DF.Table[ProductUnits]
		purchase_price: DF.Currency
		revenue_group: DF.Link | None
		show_in_customer_product_price: DF.Check
		sort_order: DF.Int
		stock_location: DF.Link | None
		unit: DF.Link
	# end: auto-generated types

	_DOCTYPE_NAME = "Product"


	def validate(self):
		if self.cost and not self.purchase_price:
			self.purchase_price =  self.cost
		if not self.cost and  self.purchase_price:
			self.cost = self.purchase_price
		

	def autoname(self):
		from frappe.model.naming import set_name_by_naming_series
		if strip(self.naming_series) !="" and strip(self.product_code) =="":
			set_name_by_naming_series(self)
			self.product_code = self.name		
		self.product_code = strip(self.product_code)
		self.name = self.product_code
	
	def on_update(self):
		product_outlets = []
		for a in self.product_outlet:
			product_outlets.append({"outlet":a.outlet})
		self.product_outlets = json.dumps(product_outlets)
		update_product_unit(self)

		# update inventory transaction
		if self.has_value_changed("is_inventory_product"):
			self.validate_product_use_in_inventory_transaction()
			

		# self.update_stock()

	def after_insert(self):
		if self.is_inventory_product==1:
			self.update_stock()

	@frappe.whitelist()
	def get_stats(self):
		
		sql="select stock_location as label,quantity, quantity as value,cost  from `tabStock Location Products` where product_code=%(product_code)s"
		data = frappe.db.sql(sql,{"product_code":self.name},as_dict = 1)
		
		if data:
			data.append({
				"label":_("Total"),
				"value": sum([d.get("value") for d in data])
				
			})
		# format number
		for d in data:
			d["value"] = frappe.format(d.get("value"),{"fieldtype":"Float"})


		if data:
			stock_value = sum([(d.get("quantity") or  0)* (d.get("cost") or 0) for d in data ])
			
			data.append({

				"label":_("Stock Value"),
				"value":frappe.format(stock_value or 0,{"fieldtype":"Currency"}),
				
			})
			
		return data
	
	def update_stock(self):
		

		add_inventory_transaction([
			{
			"ref_doctype":self.doctype,
			"ref_docname":self.name,
			"posting_date":frappe.utils.getdate(self.creation),
			"stock_location":self.stock_location,
			"product_code":self.name,
			"unit":self.unit,
			"quantity": self.opening_quantity,
			"multiplier":1,
			"cost":self.cost,
			"is_calculate_cost": 0 if self.costing_method == "Fixed Cost" else 1,
			"note": "ចំនួនដើមគ្រា"
		}
		])

	

	def validate_product_use_in_inventory_transaction(self):
		if self.is_inventory_product == 0:

			# check if product have in inventory transaction
			sql = "select name from `tabInventory Transactions` where ref_doctype<>'Product'and product_code =%(product_code)s"
			if frappe.db.sql(sql,{"product_code":self.product_code}):
				frappe.throw(_("This product has been use in inventory transaction. We can not change this to none inventory tracking product."))
			
			self.opening_quantity = 0
			self.cost = 0
			# delete opening transaction and delete product from stock lodation product
			frappe.db.sql("delete from `tabInventory Transactions` where product_code = %(product_code)s",{"product_code":self.name})
			frappe.db.sql("delete from `tabStock Location Products` where product_code = %(product_code)s",{"product_code":self.name})
	@frappe.whitelist()
	def get_stock_location_product_for_adjustment(self):
		sql = """
			select 
				a.name as stock_location,
				coalesce(b.quantity,0) as current_quantity,
				coalesce(b.quantity,0) as new_quantity,
				coalesce(b.cost,0) as current_cost,
				coalesce(b.cost,0) as new_cost
			from `tabStock Location` a
			left join `tabStock Location Products`  b on a.name = b.stock_location and b.product_code = %(product_code)s
		"""
		data = frappe.db.sql(sql, {"product_code":self.name},as_dict = 1)
		return data
	
	@frappe.whitelist()
	def update_stock_adjustment(self):
		if [d for d in self.stock_adjustment_data if d.get("new_quantity")<0]:
			frappe.throw(_("Quantity cannot less than 0"))
			
		if [d for d in self.stock_adjustment_data if d.get("new_cost")<0]:
			frappe.throw(_("Cost cannot less than 0"))

		# update quantity adjustment 
		add_inventory_transaction([
			{
				"ref_doctype":self.doctype,
				"ref_docname":self.name,
				"posting_date":frappe.utils.getdate(frappe.utils.now()),
				"stock_location":p.get("stock_location"),
				"product_code":self.name,
				"unit":self.unit,
				"quantity": (p.get("new_quantity") or 0 ) - (p.get("current_quantity") or 0),
				"multiplier":0,
				"is_calculate_cost":0,
				"cost":p.get("current_cost") or 0,
				"note": "កែប្រែចំនួនទំនិញ"
			}
			for p in self.stock_adjustment_data
			if 
			((p.get("new_quantity") or 0) != (p.get("current_quantity") or 0))  
		])
		# cost
		add_inventory_transaction([
			{
				"ref_doctype":self.doctype,
				"ref_docname":self.name,
				"posting_date":frappe.utils.getdate(frappe.utils.now()),
				"stock_location":p.get("stock_location"),
				"product_code":self.name,
				"unit":self.unit,
				"quantity": 0,
				"multiplier":1,
				"is_calculate_cost": 0 if self.costing_method == "Fixed Cost" else 1,
				"cost":p.get("new_cost") or 0,
				"note": "កែប្រែថ្លៃដើម"
			}
			for p in self.stock_adjustment_data
			if 
			((p.get("new_cost") or 0) != (p.get("current_cost") or 0))  
		])

		

		frappe.msgprint(_("Update stock adjustment successfully"))

@redis_cache
def get_product_price(product_code,unit,customer=None):
	price = None
	if customer:
		price_data = frappe.db.sql("select coalesce(max(multiplier),1) as multiplier, coalesce(max(price),0) as price from `tabCustomer Product Price` where parent=%(customer)s and product_code =%(product_code)s and unit = %(unit)s",{

			"product_code":product_code,
			"unit":unit,
			"customer":customer
		},as_dict = 1)
		if len(price_data)>0:
			
			if  price_data[0].get("price")>0:
				price = price_data[0]

	if not price:
		price_data = frappe.db.sql("select coalesce(max(multiplier),1) as multiplier, coalesce(max(price),0) as price from `tabProduct Units` where parent=%(product_code)s  and  unit = %(unit)s",
			{
			"product_code":product_code,
			"unit":unit
		},as_dict = 1)
		if len(price_data)>0:
			if  price_data[0].get("price")>0:
				price = price_data[0]
	if not price:
		price = {
			"price":frappe.get_cached_value("Product",product_code,"price"),
			"multiplier": frappe.get_cached_value("Unit",frappe.get_cached_value("Product",product_code,"unit"),"multiplier") or 1

		}
	
	return price
			


def update_product_unit(self):
	if len(self.product_units or [])>0:
		if self.has_value_changed("price") or self.has_value_changed("unit"):
			for a in self.product_units:
				if a.base_product_unit == 1:
					a.price = self.price
					a.unit = self.unit
					a.multiplier = 1
	else:
		self.append("product_units", {
				"unit":self.unit,
				"multiplier": self.multiplier,
				"price": self.price,
				"base_product_unit": 1
			})
 