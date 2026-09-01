
import frappe
from frappe import _
from frappe.model.document import Document
import json
from datetime import datetime, date
from ice_control.api.utils import validate_close_date,get_sale_product_changed,get_exchange_rate,get_current_employee_outlets
from ice_control.api.inventory import add_inventory_transaction,get_stock_location_prouct,get_product_units_multiplier
from ice_control.selling.doctype.sale.accounting import submit_to_gl_entry


class Sale(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.selling.doctype.pos_sale_payment.pos_sale_payment import POSSalePayment
		from ice_control.selling.doctype.sale_products.sale_products import SaleProducts

		amended_from: DF.Link | None
		balance: DF.Currency
		booking_number: DF.Link | None
		can_edit_bill: DF.Check
		can_show_price: DF.Check
		can_split_bill: DF.Check
		created_by: DF.Data | None
		customer: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		customer_photo: DF.AttachImage | None
		deleted_by: DF.Data | None
		deleted_date: DF.Datetime | None
		deleted_note: DF.Data | None
		driver: DF.Link | None
		driver_name: DF.Data | None
		driver_phone_number: DF.Data | None
		driver_photo: DF.AttachImage | None
		id: DF.Data | None
		last_update_station: DF.Link | None
		naming_series: DF.Literal["SO.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link | None
		outlet_unit: DF.Link | None
		parent_bill_number: DF.Link | None
		payments: DF.Table[POSSalePayment]
		phone_number: DF.Data | None
		plate_number: DF.Data | None
		posting_date: DF.Date
		product_qty: DF.LongText | None
		reference_number: DF.Data | None
		sale_products: DF.Table[SaleProducts]
		sale_status: DF.Literal["Draft", "Closed", "Deleted"]
		seller: DF.Data | None
		station: DF.Link | None
		status: DF.Literal["Unpaid", "Paid", "Partially Paid", "Deleted"]
		stock_location: DF.Link | None
		total_amount: DF.Currency
		total_free: DF.Float
		total_payment: DF.Currency
		total_quantity: DF.Float
		total_quantity_return: DF.Float
		total_sale_quantity: DF.Float
		total_split_bill: DF.Int
		total_split_quantity: DF.Float
		total_write_off: DF.Currency
		update_from: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Sale"


	def validate(self):
		
		self.validate_require_fields()
		validate_close_date(self.posting_date,self.creation,self.outlet)
		if(self.parent_bill_number):
			# check if customer already have split bill
			if self.is_new() and  frappe.db.exists("Sale",{"parent_bill_number":self.parent_bill_number,"customer":self.customer,"sale_status":"Closed"}):
				frappe.throw("អតិថិជន <strong>{0}</strong> បានបំបែកបុងរួចហើយ".format(self.customer_name))
				
			validate_parent_bill_on_split_bill(self=self, name = self.parent_bill_number)
			validate_parent_bill_quantity(self)

		self.validate_permission()

		
		get_customer_product_price(self)
		
		self.validate_sale_products()
		verify_product(self)
		self.validate_sale()
		self.update_total_amounts()
		self.validate_payments()

		update_payment_status(self)
		# validate parent bill if this bill is a split bill

	def validate_sale_products(self):
		# validte sale product quantity vs return vs free 
		_invalid_products = [
								x for x 
								in self.sale_products 
								if (x.quantity or 0) - ((x.free_quantity or 0) + (x.return_quantity or 0) + (x.split_quantity or  0)) <0 
							]

		for d in _invalid_products:
			frappe.throw(
				f"ទំនិញនៅជួរទី {d.idx} ({d.product_name})៖ "
				f"ចំនួនសល់មកវិញ + ចំនួនថែម/Free + ចំនួនបំបែក "
				f"មិនអាចលើសចំនួនដើមបានទេ។"
			)
	
		# validate product valid outlet
		if self.sale_products:
			_product_codes = [x.get("product_code") for x in self.sale_products]
			_product_codes = _product_codes or []
			if len(_product_codes)>0:
				sql="""
						select parent as product_code,outlet from `tabProduct Outlet` a
						where
							parent in %(product_codes)s and outlet = %(outlet)s
					
				"""
				_product_outlets = frappe.db.sql(sql,{"product_codes":_product_codes,"outlet":self.outlet},as_dict=1)
				for sp in self.sale_products:
					if len([x for x in _product_outlets if x.get("product_code") == sp.product_code])==0:
						frappe.throw("ទំនិញ {0} មិនអាច់លក់នៅទីតាំងលក់ {1} បានទេ។".format(sp.product_name, self.outlet))
				
		


	def validate_sale(self):
		if not self.is_new():
			#validate if bill change from close back to draft
			#not allow to change change back to draft
			old_doc = self.get_doc_before_save()

			if old_doc.sale_status == "Deleted":
				frappe.throw("បុងនេះបានលុបរួចហើយ")

			if old_doc.sale_status == "Closed" and  self.sale_status=="Draft":
				frappe.throw("បុងដែលបានបិទមិនអាចកែប្រែទៅជាដាក់រង់ចាំបានទេ")
			# validate if bill has payment
			sql="select name from `tabSale Payment Invoices` where docstatus in (0,1) and sale=%(sale)s limit 1"
			data = frappe.db.sql(sql,{"sale":self.name})
			 
			if data:
				if self.sale_status == "Deleted":
					frappe.throw("អ្នកមិនអាចលុបសបុងដែលមានប្រតិបត្តិការបង់ប្រាក់ទេ")
				else:
					frappe.throw("អ្នកមិនអាចកែប្រែបុងដែលមានប្រតិបត្តិការបង់ប្រាក់ទេ")
			if not self.parent_bill_number:
				if self.has_value_changed("customer"):
					if frappe.db.exists("Sale",{"parent_bill_number":self.name,"sale_status":["in",["Draft","Closed"]]}):
						frappe.throw("អ្នកមិនអាចប្តូរអតិថិជនបានទេ ព្រោះបុងនេះបានបំបែករួចហើយ")

				# validate delete

	def autoname(self):
		if self.is_new() and self.parent_bill_number:
			from frappe.model.naming import make_autoname
			self.name =  make_autoname(self.parent_bill_number + ".-.##")



	def validate_require_fields(self):

		if self.sale_status=='Closed' and not self.customer:
			frappe.throw(_("Please select customer"))

		get_employee_name(self)

	def validate_payments(self):
		if self.payments:
			for p in self.payments:
				p.exchange_rate = get_exchange_rate(p.currency, frappe.get_cached_value("Business Information",None,"default_currency"))
				
				p.payment_amount = (p.input_amount or 0) * ( float( p.exchange_rate) or 1)

			self.total_payment = sum([x.payment_amount or 0 for x in self.payments])
		else:
			self.total_payment = 0

		self.balance = self.total_amount - self.total_payment
		if self.balance<0:
			self.balance = 0
		
		update_payment_status(self)
		

		
		 


	# other doc method
	@frappe.whitelist()
	def update_sale_information(self):
		pass
		# # this function to recalculate sale total when form open improve data consistency
		# frappe.db.sql("call sp_update_sale_information ('{}','')".format(self.name))

	@frappe.whitelist()
	def get_payment_history_for_frappe_data_table(self):

		columns = [
			{ "id": 'payment_date', "name": _('Payment Date'),   "width": 120, "align":"center"},
			{ "id": 'receipt_number', "name": _('Receipt No'),   "width": 150 ,"align":"center"},
			{ "id": 'payment_amount', "name": _('Payment Amount'),   "width": 150,"align":"right" },
			{ "id": 'write_off_amount', "name": _('Write Off Amount'),   "width": 150 ,"align":"right"},
			{ "id": 'created_by', "name": _('Created By'),   "width": 120 },
			{ "id": 'created_date', "name": _('Created Date'),   "width": 200 },
			{ "id": 'note', "name": _('Note'),"width":250,"align":"left"   },
		]

		sql = "select payment_date,parent as receipt_number,payment_amount,write_off_amount, note, owner as created_by, creation as created_date from `tabSale Payment Invoices` where sale = %(sale)s and docstatus = 1"
		data  = frappe.db.sql(sql, {"sale":self.name},as_dict = 1)
		# apply formating
		for d in data:
			d["payment_date"] = frappe.format(d.get("payment_date"),{"fieldtype":"Date"})
			d["created_date"] = frappe.format(d.get("created_date"),{"fieldtype":"Datetime"})
			d["payment_amount"] = frappe.format(d.get("payment_amount"),{"fieldtype":"Currency"})
			d["write_off_amount"] = frappe.format(d.get("write_off_amount"),{"fieldtype":"Currency"})
		return {
			"columns":columns,
			"data":data,
			"layout": 'fitColumns',
			 "selectable": False,
    "editable": False
		}

	@frappe.whitelist()
	def get_payment_history(self):
		sql = """
		select 
			p.posting_date,
			s.parent as receipt_number,
			s.payment_amount,
			s.write_off_amount, 
			s.note, 
			p.created_by,
			p.creation as created_date 
			from `tabSale Payment Invoices` s
			join `tabSale Payment` p on p.name = s.parent
			 where s.sale = %(sale)s and p.docstatus = 1"""
		data  = frappe.db.sql(sql, {"sale":self.name},as_dict = 1)
		return   data

	def on_update(self):
		if self.flags.get("ignore_update"):
			return
		if self.sale_status == "Closed":
			# dont for get more this to eqnueue
			# frappe.enqueue("ice_control.selling.doctype.sale.sale.update_stock_product",queue="short",self=self)
			update_stock_product(self)
			if self.parent_bill_number:
				# we commit this to update quantity to db 
				frappe.db.commit()

				update_split_quantity_to_parent_bill(self.parent_bill_number)
			if self.payments:
				add_pos_payment_to_sale_payment(self)
				# frappe.enqueue("ice_control.selling.doctype.sale.sale.add_pos_payment_to_sale_payment",queue="short",self=self)

			# update to borrow product
			frappe.enqueue("ice_control.selling.doctype.sale.sale.update_borrow_product",queue="short",old_doc=self.get_doc_before_save() ,new_doc=self)
			# update_borrow_product(self.get_doc_before_save() ,self)

			# add sale data to gl entry
			submit_to_gl_entry(self)


		elif self.sale_status == "Deleted":
			update_stock_product(self)
			# add comment
			comment_text = f"""
			<br/>
				<strong style='color:red'>លុបបុង</strong> <br/>
				មូលហេតុលុបបុង៖ <strong>{self.deleted_note}</strong>
			"""
			self.add_comment('Deleted', comment_text)
			# cancell all borrow product
			cancell_all_borrow_product(self)
			if self.parent_bill_number:
				frappe.db.commit()
				update_split_quantity_to_parent_bill(self.parent_bill_number)
		if self.parent_bill_number:
			# we commit this to update quantity to db 
			frappe.enqueue("ice_control.selling.doctype.sale.sale.update_sub_bill_audit_trail",queue="short",old_doc = self.get_doc_before_save() ,new_doc = self)
			# update_sub_bill_audit_trail(self.get_doc_before_save() ,self)

	def update_total_amounts(self):		
		self.total_quantity = (sum((d.quantity or 0) for d in self.sale_products if d.allow_sum_qty == 1) or 0)
		self.total_free = (sum((d.free_quantity or 0) for d in self.sale_products if d.allow_sum_qty == 1) or 0)
		self.total_quantity_return = (sum((d.return_quantity or 0) for d in self.sale_products if d.allow_sum_qty == 1) or 0)
		self.total_split_quantity = (sum((d.split_quantity or 0) for d in self.sale_products if d.allow_sum_qty == 1) or 0)
		self.total_sale_quantity = (self.total_quantity or 0)  - ((self.total_free or 0) + (self.total_quantity_return or 0) + (self.total_split_quantity or 0))
		self.total_amount = sum([x.get("total_amount") for x in self.sale_products if x.allow_sum_qty==1])
		self.total_payment = 0
		self.balance = self.total_amount - (self.total_payment or 0)
		self.product_qty = generate_product_qty(self.sale_products)

	def validate_permission(self):
		if frappe.session.user == "Administrator":
			return
		employee = frappe.db.exists("Employee",{"user_id":frappe.session.user})
		employee_doc = {"change_sale_date_after_save":0,"change_customer_after_close_sale":0}
		if employee:
			employee_doc = frappe.get_cached_doc("Employee",employee)
		old_doc = self.get_doc_before_save()
		if not self.is_new():
			if self.has_value_changed("posting_date"):
				if not employee_doc.change_sale_date_after_save:
					frappe.throw("អ្នកមិនមានសិទ្ធកែប្រែកាលបរិច្ឆេទចេញវិកយប័ត្របន្ទាប់ពីវិកយប័ត្របានបិទទេ")
			# validate allow change customer from sale order
			if not old_doc.sale_status == "Draft" and self.sale_status == "Closed":
				if self.has_value_changed("customer") and not employee_doc.change_customer_after_close_sale:
					frappe.throw("អ្នកមិនមានសិទ្ធកែប្រែអតិថិជនក្នុងបុងបានទេ")
	# this method run form 
	@frappe.whitelist(methods=["POST"])
	def change_customer(self):
		if not self.customer:
			return
		for sp in self.sale_products:
			if sp.product_code and sp.unit:
				sp.price = get_product_price(self.customer,sp.product_code, sp.unit)
				sp.product_price = sp.price
				sp.sub_total = (sp.total_sale_quantity or 0)  * (sp.price or 0)
				sp.total_amount = (sp.total_sale_quantity or 0)  * (sp.price or 0)
	
	# sale product method
	@frappe.whitelist(methods=["POST"])
	def sale_product_update(self,row:dict, check_customer_price:bool=False):
		sp = next((x for x in self.sale_products if x.name == row.get("name")),None)
		if sp:
			if check_customer_price and self.customer and sp.product_code and sp.unit:
				sp.price = get_product_price(self.customer, sp.product_code, sp.unit )
				sp.product_price = sp.price
			sp.quantity = row.get("quantity") 
			sp.total_sale_quantity = row.get("quantity") - ((row.get("free_quantity") or 0) + (row.get("return_quantity") or 0) + (row.get("split_quantity") or 0))
			sp.sub_total = (sp.total_sale_quantity or 0)  * (sp.price or 0)
			sp.total_amount = (sp.total_sale_quantity or 0)  * (sp.price or 0)
			if sp.total_sale_quantity<0:
				frappe.throw("ចំនួនសល់មកវិញ + ចំនួនថែម/Free + ចំនួនបំបែក មិនអាចលើសចំនួនដើមបានទេ។")
			self.update_total_amounts()

 


	def before_delete(self):
		frappe.throw("បុងលក់មិនអនុញ្ញាតអោយលុបបានទេ")
	def on_trash(self):
		frappe.throw("បុងលក់មិនអនុញ្ញាតអោយលុបបានទេ")

def get_product_price(customer:str, product_code:str,unit:str):
	filter = {
		"customer":customer,
		"product_code":product_code,
		"unit":unit
	}
	price = 0
	sql="select max(price) as price from `tabCustomer Product Price` where product_code=%(product_code)s and unit=%(unit)s and parent=%(customer)s" 
	data = frappe.db.sql(sql,filter,as_dict=1)
	
	if data:
		price = data[0].get("price") or 0

		if price>0:
			frappe.msgprint("ទំនិញ៖ {0} ត្រូវបានកំណត់តម្លៃតាមអតិថិជន".format(frappe.get_cached_value("Product",product_code,"product_name")))
			return price
	# get from product unit
	sql="select price from `tabProduct Units` where parent=%(product_code)s and unit=%(unit)s order by creation desc" 
	data = frappe.db.sql(sql,filter,as_dict=1)
	if data:
		price= data[0].get("price") or 0
		if price>0:
			return price
		else:
			return 0
	else:
		multiplier = get_product_units_multiplier(product_code,unit)
		frappe.msgprint("Product <strong>{0}</strong> do not have price for unit <strong>{1}</strong>. Please change price manually".format(frappe.get_cached_value("Product",product_code,"product_name"),unit))
		return frappe.get_cached_value("Product", product_code,"price")*(multiplier or 1)

def get_employee_name(self):
	if self.seller:
		return
	if frappe.session.user == "Administrator":
		self.seller = "Administrator"
		return
	name = frappe.db.get_value('Employee', {'user_id':self.owner}, 'employee_name')
	self.seller = name

@frappe.whitelist()
def query_permission(user):
	from ice_control.api.auth import get_employee_outlets
	if frappe.session.user !="Administrator":
		outlets = get_employee_outlets()
		escaped_outlets = ", ".join(
		frappe.db.escape(outlet) for outlet in outlets
		)
		return f"`tabSale`.outlet IN ({escaped_outlets})"
	return ""

@frappe.whitelist()
def update_stock_product(self):
	sale_products = []
	if self.sale_status == "Closed":
		sale_products = [
			{
				"product_code":p.product_code,
				"unit":p.unit,
				"multiplier":p.multiplier,
				"stock_location":p.stock_location or self.stock_location,
				"quantity": p.quantity+ (p.free_quantity or 0)  -  (p.return_quantity or 0)
			}
			for p in  self.sale_products
		]
		product_codes =  list({(d["product_code"], d["unit"],d["stock_location"],d["multiplier"]) for d in sale_products})
		data = [
			{
				"ref_doctype":self.doctype,
				"ref_docname":self.name,
				"posting_date":self.posting_date,
				"stock_location":p[2], #stock location index
				"product_code":p[0],
				"unit":p[1],
				"multiplier":p[3],
				"quantity": sum([d.get("quantity") for d in sale_products if d.get("product_code") == p[0] and d.get("unit") == p[1]]) * -1,
				"is_calculate_cost":0,
			}
			for p in product_codes
		]
		add_inventory_transaction(data)

def verify_product(self):
	from ice_control.stock_management.doctype.product.product import get_product_price
	error = ""
	for a in self.sale_products:
		a.outlet = self.outlet
		if not a.stock_location:
			a.stock_location = self.stock_location



		product_info = get_product_price(a.product_code,a.unit,self.customer)
		a.product_price = product_info.get("price",0)

		a.total_sale_quantity = (a.quantity or 0) -((a.free_quantity or 0) + (a.return_quantity or 0) + (a.split_quantity or 0))


		a.multiplier = get_product_units_multiplier(a.product_code,a.unit)
		a.total_amount = a.price * a.total_sale_quantity * a.multiplier
		a.sub_total = a.price * a.total_sale_quantity * a.multiplier




		# update cost
		if a.is_inventory_product == 1:
			stock_location_product = get_stock_location_prouct(a.product_code, a.stock_location or self.stock_location)
			if stock_location_product:
				a.cost = stock_location_product.get("cost")
				a.total_cost = a.cost * ((a.total_sale_quantity or 0) + (a.free_quantity or 0))
			else:
				a.cost = a.price
				a.total_cost = a.cost * ((a.total_sale_quantity or 0) + (a.free_quantity or 0))




		if a.total_amount < 0 and (a.get("product_code") or"") != "":
			error += (_("<b>{0}</b> Product <b>{1}</b> total amount can not be small than zero").format((self.name if self.update_from  != "Sale" else ""),a.product_name))
		if error != "":
			frappe.throw(error)




def update_payment_status(self):
	if self.sale_status == "Deleted":
		self.status = "Deleted"
		return
	if self.balance == 0:
		self.status = "Paid"
	elif self.balance > 0 and self.balance < self.total_amount:
		self.status = "Partially Paid"
	else:
		self.status = "Unpaid"

def get_customer_product_price(self):
	return
	# we use client to update this data
	customer_free_products = frappe.db.sql("""SELECT product_code,quantity,unit,multiplier FROM `tabCustomer Free Products` WHERE parent = '{}'""".format(self.customer),as_dict=1)
	if len(customer_free_products)>0:
		for a in customer_free_products:
			for b in self.sale_products:
				if (a.get("product_code") or "") == b.product_code:
					b.free_quantity = (a.get("quantity") or 0) * (a.get("multiplier",1)/b.get("multiplier",1))
					b.total_sale_quantity = b.quantity - b.free_quantity
					b.total_amount = b.price * b.total_sale_quantity
					b.sub_total = b.price * b.quantity



@frappe.whitelist()
def generate_product_qty(sale_products: str | list | None = None):
	from collections import defaultdict
	if isinstance(sale_products, str):
		if sale_products != "":
			sale_products = json.loads(sale_products)
			group = defaultdict(lambda: {"total_sale_quantity": 0, "total_amount": 0})
			for item in sale_products:
				if (item.get("product_code") or "") != "":
					key = item.get("revenue_group")
					group[key]["total_sale_quantity"] += (item.get("total_sale_quantity") or 0)
					group[key]["total_amount"] += (item.get("total_amount") or 0)
			result = [{"revenue_group": key, "total_sale_quantity": val["total_sale_quantity"], "total_amount": val["total_amount"]}for key, val in group.items()]
			return json.dumps(result)
	else:
		if len(sale_products or []) > 0:
			group = defaultdict(lambda: {"total_sale_quantity": 0, "total_amount": 0})
			for item in sale_products:
				if (item.get("product_code") or "") != "":
					key = item.get("revenue_group") or ""
					# group[key]["total_sale_quantity"] += item.total_sale_quantity
					# group[key]["total_amount"] += item.total_amount
					group[key]["total_sale_quantity"] += item.get("total_sale_quantity") or 0
					group[key]["total_amount"] += item.get("total_amount") or 0
			result = [{"revenue_group": key, "total_sale_quantity": val["total_sale_quantity"], "total_amount": val["total_amount"]}for key, val in group.items()]
			return json.dumps(result)

@frappe.whitelist()
def get_sales(start_date="",end_date="",customer="",outlet=""):
	conditions = ""
	if start_date !="":
		conditions += " and posting_date >= '{}'".format(start_date)
	if end_date !="":
		conditions += " and posting_date <= '{}'".format(end_date)
	if customer != "":
		conditions += " and customer = '{}'".format(customer)
	if outlet != "":
		conditions += " and outlet = N'{}'".format(outlet)
	sql = """SELECT name sale,total_amount, balance FROM `tabSale` WHERE status <> 'Paid' {}""".format(conditions)

	sales = frappe.db.sql(sql, as_dict=1)
	return (sales or [])

@frappe.whitelist()
def validate_edit_sale_action(name):
	employee = frappe.db.exists("Employee",{"user_id":frappe.session.user})
	employee_doc = frappe.get_cached_doc("Employee",employee)
	if not employee_doc.edit_bill:

		frappe.throw("អ្នកមិនមានសិទ្ធកែប្រែបុងទេ")
	sale_doc = frappe.get_cached_doc("Sale",name)

@frappe.whitelist()
def get_sale_for_edit(name:str,station_name:str = "")->dict:
	if not frappe.db.exists("Sale",name):
		frappe.throw("មិនមានបុងលេខ {} នៅក្នុងប្រព័ន្ធទេ".format(name))
	sale_doc = frappe.get_doc("Sale",name)
	if sale_doc.sale_status =="Deleted":
		frappe.throw("បុងលេខ {} ត្រូវបានលុប".format(name))

	if sale_doc.parent_bill_number:
		frappe.throw("អ្នកមិនអាចកែបុងបំបែកបានទេ")
	# check if bill is draft then return data
	if sale_doc.sale_status == "Draft":
		audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale_doc.name,
			"outlet":sale_doc.outlet,
			"posting_date":frappe.utils.now(),
			"station":station_name,
			"audit_trail_type":"កែប្រែបុង",
			"description": "បើកបុងកំពុងរង់ចាំដើម្បីកែប្រែ"
		}
		frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)
		return sale_doc

	# validate if user can access sale outlet
	outlets = frappe.db.get_list('Outlet',pluck='name')
	if not sale_doc.outlet in outlets:
		audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale_doc.name,
			"posting_date":frappe.utils.now(),
			"station":station_name,
			"audit_trail_type":"កែប្រែបុង",
			"description": "ព្យាយាមបើកបុងដើម្បីកែប្រែ ប៉ុន្តែគ្មានសិទ្ធកែប្រែបុងនៅកន្លែលកល {} ទេ។".format(frappe.get_cached_value("Outlet",sale_doc.outlet,"outlet_name_kh"))
		}
		frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)
		frappe.throw("អ្នកមិនមានសិទ្ធកែប្រែបុងនៅកន្លែងលក់ {}ទេ".format(frappe.get_cached_value("Outlet",sale_doc.outlet,"outlet_name_kh")))
	# validate permission
	employee = frappe.db.exists("Employee",{"user_id":frappe.session.user})
	employee_doc = frappe.get_cached_doc("Employee",employee)
	if not employee_doc.edit_bill:
		audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale_doc.name,
			"posting_date":frappe.utils.now(),
			"station":station_name,
			"audit_trail_type":"កែប្រែបុង",
			"description": "ព្យាយាមបើកបុងដើម្បីកែប្រែ។ ប៉ុន្តែមិនមានសិទ្ធកែប្រែបុង។"
		}
		frappe.enqueue(".api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)

		frappe.throw("អ្នកមិនមានសិទ្ធកែប្រែបុងទេ")


	# sale has payment
	sql="select name from `tabSale Payment Invoices` where docstatus in (0,1) and sale=%(sale)s limit 1"
	data = frappe.db.sql(sql,{"sale":sale_doc.name})

	if data:
		audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale_doc.name,
			"posting_date":frappe.utils.now(),
			"station":station_name,
			"audit_trail_type":"កែប្រែបុង",
			"description": "ព្យាយាមបើកបុងដែលមានប្រតិបត្តិការបង់ប្រាក់ដើម្បីកែប្រែ"
		}
		frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)

		frappe.throw("អ្នកមិនអាចកែប្រែបុងដែលមានប្រតិបត្តិការបង់ប្រាក់ទេ")
	# valite sale has child split bill
	if frappe.db.exists("Sale",{"parent_bill_number":name,"sale_status":["!=","Deleted"]}):
		frappe.throw("អ្នកមិនអាចកែប្រែបុងនេះបានទេ ព្រោះបុងនេះបានបំបែកបុងរួចហើយ")
	# close report period
	if frappe.db.exists("Closed Selling Date",{"outlet":sale_doc.outlet, "posting_date":[">=",sale_doc.posting_date],"docstatus":1}):
		frappe.throw("អ្នកមិនអាចកែប្រែបុងនេះបានទេ។ ព្រោះថ្ងៃទី {},ទីតាំងលក់ {}   ត្រូវបានបិទបញ្ជីររួចហើយ។".format(frappe.format(sale_doc.posting_date,{"fieldtype":"Date"}),
																											frappe.get_cached_value("Outlet",sale_doc.outlet,"outlet_name_kh")))
	# check if customer is allow to edit bill
	if frappe.get_cached_value("Customer",sale_doc.customer,"can_edit_bill") == 0:
		frappe.throw("អតិថិជននេះមិនអនុញ្ញាតអោយកែប្រែបុងទេ។")

	# check if bill is a split bill validate parent if already have payment record
	if sale_doc.parent_bill_number:
		sql="select name from `tabSale Payment Invoices` where docstatus in (0,1) and sale=%(sale)s limit 1"
		data = frappe.db.sql(sql,{"sale":sale_doc.parent_bill_number})

		if len(data)>0:
			frappe.throw("អ្នកមិនអាចកែប្រែបុងនេះបានទេ ព្រោះបុងមេរបស់បុងនេះបានបង់ប្រាក់រួចហើយ")

	audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale_doc.name,
			"posting_date":frappe.utils.now(),
			"station":station_name,
			"audit_trail_type":"កែប្រែបុង",
			"description": "បើកបុងដើម្បីកែប្រែ"
		}
	frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)

	return sale_doc

def validate_sale_payment_amount(name,message):
	sql="select name from `tabSale Payment Invoices` where docstatus in (0,1) and sale=%(sale)s limit 1"
	data = frappe.db.sql(sql,{"sale":name})
	if data:
		frappe.throw(message)
def validate_has_split_bill(name,message):
	if frappe.db.exists("Sale",{"parent_bill_number":name, "sale_status":["!=","Deleted"]}):
		frappe.throw(message)


@frappe.whitelist(methods="POST")
def delete_bill(sale_doc:dict = None, doc_name:str = None,note:str = None,station_name:str = "", audit_trails:list[dict] = [])->dict:
	if not doc_name and sale_doc:
		doc_name = sale_doc.get("name")

	employee = frappe.db.exists("Employee",{"user_id":frappe.session.user})
	employee_doc = frappe.get_cached_doc("Employee",employee)
	if not employee_doc.delete_bill:
		frappe.throw("អ្នកមិនមានសិទ្ធលុបបុងទេ")


	if doc_name:
		# validate have payment
		validate_sale_payment_amount(doc_name,"អ្នកមិនអាចលុបបុងនេះបានទេ ព្រោះបុងនេះបានបង់ប្រាក់រួចហើយ")
		validate_has_split_bill(doc_name,"អ្នកមិនលុបបុងនេះបានទេ ព្រោះបុងនេះបានបំបែកបុងរួចហើយ")
		doc = frappe.get_doc("Sale",doc_name)
		doc.sale_status = "Deleted"
		doc.status= "Deleted"
		doc.deleted_date = frappe.utils.now()
		doc.deleted_note = note
		doc.deleted_by = frappe.get_cached_value("User",frappe.session.user,"full_name")
		doc.save()
		# add audit trail log
		log = {
			"audit_trail_type":"លុបបុង",
			"doctype": "Audit Trail Log",
			"posting_date":frappe.utils.now(),
			"ref_doctype":"Sale",
			"ref_doc_name":doc.name,
			"outlet":doc.outlet,
			"station":station_name or doc.get("station"),
			"description":"មូលហេតុលុបបុង៖ {0}".format(note or "")
		}
		audit_trails.append(log)
		frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trails)
		if doc.parent_bill_number:
			update_split_quantity_to_parent_bill(doc.parent_bill_number)
		return doc.as_dict()
	frappe.throw("មិនមានបុងសម្រាប់លុប")

@frappe.whitelist()
def add_pos_payment_to_sale_payment(self):
	from decimal import Decimal
	amount_to_pay = self.total_amount
	for p in self.payments:
		doc = frappe.get_doc({
			"doctype":"Sale Payment",
			"posting_date":self.posting_date,
			"outlet":self.outlet,
			"payment_type":p.payment_type,
			"customer":self.customer,
			"input_amount":p.input_amount,
			"payment_amount": p.payment_amount,
			"amount_to_pay":amount_to_pay ,
			"exchange_rate":p.exchange_rate,
			"exchange_rate_virtual":p.exchange_rate if Decimal(p.exchange_rate) >=1 else str(1/ Decimal(p.exchange_rate) ),
			"sale":self.name,
			"pos_sale_payment":p.name,
			"sales":[
				{
					"sale":self.name,
					"payment_amount":p.payment_amount,
				}
			]
		})
		doc.insert(ignore_permissions=True)

		doc.flags.ingore_validation = True
		doc.submit()
		amount_to_pay = amount_to_pay - p.payment_amount

@frappe.whitelist()
def get_payment_history(name):
	sql = """
		select 
			p.posting_date,
			s.parent as receipt_number,
			s.payment_amount,s.
			write_off_amount, 
			s.note, 
			p.creation_by
			p.creation as created_date 
			from `tabSale Payment Invoices` s
			join `tabSale Payment` p on p.name = s.parent
			 where s.sale = %(sale)s and p.docstatus = 1"""
	data  = frappe.db.sql(sql, {"sale":name},as_dict = 1)
	return data


def update_split_quantity_to_parent_bill(name:str):
	split_quantity_data = frappe.db.sql("select sp.product_code,sp.unit, sum(sp.total_sale_quantity) as quantity from `tabSale Products` sp join `tabSale` s on s.name = sp.parent where s.sale_status = 'Closed' and parent_bill_number = %(name)s group by product_code,unit",{"name":name},as_dict = 1)
	doc = frappe.get_doc("Sale",name)
	if split_quantity_data:
		for sp in doc.sale_products:
			split_sp =  next((item for item in split_quantity_data if item.get("product_code") == sp.product_code and item.get("unit") == sp.unit), None)
			if split_sp:
				
				sp.split_quantity = split_sp.quantity or 0
			else:
				sp.split_quantity = 0
	else:
		for sp in doc.sale_products:
			sp.split_quantity = 0
	doc.total_split_bill = frappe.db.count('Sale', {'parent_bill_number': name,"sale_status":"Closed"})
	doc.save()

def validate_parent_bill_on_split_bill(self=None,doc= None,name=None):
	if not doc:
		doc = frappe.get_doc("Sale",name)
	if self:
		if self.customer == doc.customer:
			frappe.throw("អ្នកមិនអាចជ្រើសរើសអតិថិជនក្នុងបុងមេមកបំបែកបុងបានទេ។")
	# 1 check if customer allow to split bill
	if frappe.get_cached_value("Customer",doc.customer,"allow_split_bill") ==0:
		frappe.throw("អតិថិជននេះមិនអនុញ្ញាតអោយបំបុងទេ។")
	# validate bill has payment
	sql="select name from `tabSale Payment Invoices` where docstatus in (0,1) and sale=%(sale)s limit 1"
	data = frappe.db.sql(sql,{"sale":doc.name})
	if data:
		frappe.throw("អ្នកមិនអាចបំបែកបុងនេះបានទេ ព្រោះបុងមេរបស់បុងនេះបានបង់ប្រាក់រួចហើយ")

def validate_parent_bill_quantity(self):
	# 3 data set quantity to compare
	data = [{"product_code":d.product_code,"total_sale_quantity":(d.quantity or 0) * -1} for d in self.sale_products if d.allow_split_bill == 1]
	parent_doc = frappe.get_doc("Sale",self.parent_bill_number)
	data = data +  [{"product_code":d.product_code,"total_sale_quantity":(d.total_sale_quantity or 0)  } for d in parent_doc.sale_products if d.allow_split_bill == 1]
	old_doc = self.get_doc_before_save()
	if old_doc:
		data = data +  [{"product_code":d.product_code,"total_sale_quantity":(d.quantity or 0)  } for d in old_doc.sale_products if d.allow_split_bill == 1]
	for product_code in set([d.get("product_code") for d in data]):
		if sum([d.get("total_sale_quantity") for d in data if d.get("product_code") == product_code])<0:
			frappe.throw(f"ចំនួនបំបែកបុងនៃ {frappe.get_cached_value('Product',product_code,'product_name')} មិនអាចធំជាងចំនួននៅក្នុងបុងដើមទេ")

@frappe.whitelist()
def validate_split_bill(doc= None,name=None):
	if not doc:
		doc = frappe.get_doc("Sale",name)
	# 1 check if customer allow to split bill
	if frappe.get_cached_value("Customer",doc.customer,"allow_split_bill") ==0:
		frappe.throw("អតិថិជននេះមិនអនុញ្ញាតអោយបំបុងទេ។")
	#2. check if bill is a  a split

@frappe.whitelist(methods="POST")
def change_reference_number(name,reference_number="",station_name=""):
	doc = frappe.get_doc("Sale",name)
	frappe.db.set_value("Sale",name,"reference_number",reference_number)
	doc.add_comment('Info',f"ប្តូរលេខយោងពី {doc.reference_number} ទៅ {reference_number}")
	frappe.msgprint("Change reference number successfully")

@frappe.whitelist()
def update_sub_bill_audit_trail(old_doc,new_doc):
	if not old_doc:
		product_description = "\n".join([
						f"{d.total_sale_quantity} {d.unit} x {d.product_code} - {d.product_name}, តម្លៃ៖ {frappe.format(d.total_amount,{'fieldtype':'Currency'})}"
						 for d in new_doc.sale_products])
		frappe.get_doc({
			"doctype":"Audit Trail Log",
			"posting_date":frappe.utils.now(),
			"station":new_doc.last_update_station or new_doc.station,
			"audit_trail_type":"បង្កើតបុងថ្មី",
			"description":f"បង្កើតបុងថ្មីចេញពីការបំបែកបុងមេលេខ {new_doc.parent_bill_number}។ អតិថិជន៖ {new_doc.customer} - {new_doc.customer_name}។ អ្នកបើកបរ៖ {new_doc.driver or new_doc.customer} - {new_doc.driver_name or  new_doc.customer_name}\nមុខទំនិញ\n{product_description}",
			"ref_doctype":"Sale",
			"ref_doc_name": new_doc.name
		}).insert(ignore_permissions=True)
	else:
		# detect change customer
		if old_doc.customer != new_doc.customer:
			frappe.get_doc({
				"doctype":"Audit Trail Log",
				"posting_date":frappe.utils.now(),
				"station":new_doc.last_update_station or new_doc.station,
				"audit_trail_type":"ប្តូរអតិថិជន",
				"description":f"ប្តូរអតិថិជនពី {old_doc.customer} - {old_doc.customer_name} ទៅ {new_doc.customer} - {new_doc.customer_name} ",
				"ref_doctype":"Sale",
				"ref_doc_name": new_doc.name
			}).insert(ignore_permissions=True)

		# find quantity change
		sale_product_changes = get_sale_product_changed(old_doc.sale_products, new_doc.sale_products)
		for sp in sale_product_changes.get("quantity_changes",[]):
			frappe.get_doc({
				"doctype":"Audit Trail Log",
				"posting_date":frappe.utils.now(),
				"station":new_doc.last_update_station or new_doc.station,
				"audit_trail_type":"ប្តូរចំនួន",
				"description":f"ប្តូរចំនួន {sp.get('product_code')} - {sp.get('product_name')} ពី {sp.get('old_quantity')} {sp.get('unit')} ទៅ {sp.get('new_quantity')} {sp.get('unit')}",
				"ref_doctype":"Sale",
				"ref_doc_name": new_doc.name
			}).insert(ignore_permissions=True)
		def get_amount(n):
			return frappe.format(n or 0, {"fieldtype":"Currency"})
		for sp in sale_product_changes.get("price_changes",[]):
			frappe.get_doc({
				"doctype":"Audit Trail Log",
				"posting_date":frappe.utils.now(),
				"station":new_doc.last_update_station or new_doc.station,
				"audit_trail_type":"ប្តូរតម្លៃ",
				"description":f"ប្តូរតម្លៃ {sp.get('product_code')} - {sp.get('product_name')} ពី {get_amount(sp.get('old_price'))}  ទៅ {get_amount(sp.get('new_price'))}",
				"ref_doctype":"Sale",
				"ref_doc_name": new_doc.name
			}).insert(ignore_permissions=True)
		for sp in sale_product_changes.get("added_products",[]):
			frappe.get_doc({
				"doctype":"Audit Trail Log",
				"posting_date":frappe.utils.now(),
				"station":new_doc.last_update_station or new_doc.station,
				"audit_trail_type":"បញ្ជូលទំនិញក្នុងបុង",
				"description":f"បញ្ជូល {sp.get('product_code')} - {sp.get('product_name')} ទៅក្នុងបុងចំនួន: {sp.get('quantity')} {sp.get('unit')}, តម្លៃ: {get_amount(sp.get('price'))}, សរុបតម្លៃ: {get_amount(sp.get('quantity') * sp.get('price'))}",
				"ref_doctype":"Sale",
				"ref_doc_name": new_doc.name
			}).insert(ignore_permissions=True)
		for sp in sale_product_changes.get("removed_products",[]):
			frappe.get_doc({
				"doctype":"Audit Trail Log",
				"posting_date":frappe.utils.now(),
				"station":new_doc.last_update_station or new_doc.station,
				"audit_trail_type":"លុបទំនិញចេញពីបុង",
				"description":f"លុបទំនិញ {sp.get('product_code')} - {sp.get('product_name')} ចំនួន: {sp.get('quantity')} {sp.get('unit')}, តម្លៃ: {get_amount(sp.get('price'))}, សរុបតម្លៃ: {get_amount(sp.get('quantity') * sp.get('price'))}",
				"ref_doctype":"Sale",
				"ref_doc_name": new_doc.name
			}).insert(ignore_permissions=True)

@frappe.whitelist(methods="POST")
def change_sale_date(sale,date,station_name=""):
	sale_doc = frappe.get_doc("Sale",sale)
	if sale_doc.posting_date == date:
		return
	validate_close_date(sale_doc.posting_date, frappe.utils.now(), sale_doc.outlet)
	validate_close_date(date,frappe.utils.now(), sale_doc.outlet)
	

	# already have payment
	if sale_doc.total_payment> 0:
		frappe.throw("អ្នកមិនអាចកែថ្ងៃចេញបុងនេះបានទេ ព្រោះបុងនេះបានបង់ប្រាក់រួចហើយ")
	sql = "select name from `tabSale Payment Invoices` where sale=%(sale)s and docstatus <> 2"
	data = frappe.db.sql(sql,{"sale":sale})
	if data:
		frappe.throw("អ្នកមិនអាចកែថ្ងៃចេញបុងនេះបានទេ ព្រោះបុងនេះបានបង់ប្រាក់រួចហើយ")
	# split bill
	if sale_doc.total_split_bill>0:
		frappe.throw("អ្នកមិនអាចកែថ្ងៃចេញបុងនេះបានទេ ព្រោះបុងនេះបានបំបែកបុងរួចហើយ")

	sql = "update `tabSale` set posting_date = %(posting_date)s where name = %(sale)s"
	frappe.db.sql(sql,{
		"sale":sale,
		"posting_date":date
	})
	# update gl
	sql = "update `tabGL Entry` set posting_date = %(date)s where voucher_type='Sale' and voucher_no=%(sale)s"
	frappe.db.sql(sql,{"date":date,"sale":sale})
	# update stock location
	sql = "update `tabInventory Transactions` set posting_date = %(date)s where ref_doctype='Sale' and ref_docname=%(sale)s"
	frappe.db.sql(sql,{"date":date,"sale":sale})
	# update sale payment
	# add to audit trail
	def get_date(date):
		return frappe.format(date,{"fieldtype":"Date"})
	audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale,
			"outlet":sale_doc.outlet,
			"posting_date":frappe.utils.now(),
			"station":station_name,
			"audit_trail_type":"ប្តូរថ្ងៃចេញបុង",
			"description": f"ប្តូរថ្ងៃចេញបុងពី {get_date(sale_doc.posting_date)} ទៅ {get_date(date)}"
		}
	frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)

@frappe.whitelist(methods="POST")
def change_driver(sale,data):
	saleDoc = frappe.get_doc("Sale",sale)
	if saleDoc.parent_bill_number:
		frappe.throw("បុងបំបែកមិនអាចប្តូរ ឬលុបអ្នកបើកបរចេញពីបុងបានទេ")
	sql = "update `tabSale` set driver=%(driver)s, driver_name=%(driver_name)s,driver_phone_number=%(phone_number)s, driver_photo=%(photo)s where name = %(sale)s"
	data["sale"] = sale
	frappe.db.sql(sql,data)
	# audit trail
	if saleDoc.driver and  data.get("driver"):
		# update to sub bill
		sql = "update `tabSale` set driver=%(driver)s, driver_name=%(driver_name)s,driver_phone_number=%(phone_number)s, driver_photo=%(photo)s where parent_bill_number = %(sale)s"
		frappe.db.sql(sql,data)
		frappe.msgprint("ប្តូរអ្នកបើកបរបានសម្រេច")
		# change driver
		audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale,
			"outlet":saleDoc.outlet,
			"posting_date":frappe.utils.now(),
			"station":data.get("station_name"),
			"audit_trail_type":"ប្តូរអ្នកបើកបរ",
			"description": f"ប្តូរអ្នកបើកបរពី {saleDoc.driver} - {saleDoc.driver_name} ទៅ {data.get('driver')} - {data.get('driver_name')}"
		}
		frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)
	elif saleDoc.driver and not data.get("driver"):
		# remove driver
		# update to sub bill
		sql = "update `tabSale` set driver=%(driver)s, driver_name=%(driver_name)s,driver_phone_number=%(phone_number)s, driver_photo=%(photo)s where parent_bill_number = %(sale)s"
		frappe.db.sql(sql,{"driver":saleDoc.customer,"driver_name":saleDoc.customer_name,"phone_number":saleDoc.phone_number,"photo":saleDoc.customer_photo,"sale":sale})

		frappe.msgprint("លុបអ្នកបើកបរចេញពីបុងបានសម្រេច")
		audit_trail_doc = {
			"ref_doctype":"Sale",
			"ref_doc_name":sale,
			"outlet":saleDoc.outlet,
			"posting_date":frappe.utils.now(),
			"station":data.get("station_name"),
			"audit_trail_type":"លុបអ្នកបើកបរចេញពីបុង",
			"description": f"លុបអ្នកបើកបរ៖ {data.get('driver')} - {data.get('driver_name')} ចេញពីបុង"
		}
		frappe.enqueue("ice_control.api.utils.add_audit_trail_log",queue="short",data=audit_trail_doc)
	frappe.db.commit()
	return frappe.get_doc("Sale",sale)

@frappe.whitelist()
def update_borrow_product(old_doc,new_doc):
	change_data = get_sale_product_changed(
		[d for d in old_doc.sale_products if d.sale_transaction_type == "Borrow"] if old_doc else [],
		[d for d in new_doc.sale_products if d.sale_transaction_type == "Borrow"],
		"name"
		)
	# add new product
	for p in change_data.get("added_products"):
		doc = frappe.get_doc({
				"doctype":"Borrow Product",
				"posting_date":new_doc.posting_date,
				"outlet":new_doc.outlet,
				"stock_location":p.get("stock_location"),
				"customer":new_doc.customer,
				"product":p.get("product_code"),
				"quantity":p.get("quantity"),
				"reference_doctype":"Sale",
				"reference_name":new_doc.name,
				"sale_product_id":p.get("name"),
				"note":f"ខ្ចីចេញពីបុងលេខ: {new_doc.name}, ចំនួន៖ {p.get('quantity')}"
			})
		doc.insert(ignore_permissions=True)
		doc.submit()
	# change quantity
	for p in change_data.get("quantity_changes"):
		borrow_id = frappe.db.exists("Borrow Product",{"sale_product_id":p.get("name")})

		if borrow_id:
			note = f"បានផ្លាស់ប្តូរចំនួនពី {p.get('old_quantity')} ទៅ {p.get('new_quantity')}  ក្នុងបុងលេខ៖ {new_doc.name}"
			frappe.db.sql("update `tabBorrow Product`  set quantity =%(quantity)s, customer=%(customer)s, customer_name=%(customer_name)s,total_cost=%(quantity)s  * cost, note=concat(note,'\n',%(note)s) where name = %(name)s",
			{
				"name":borrow_id,"quantity":p.get("new_quantity"),
				"customer":new_doc.customer,
				"customer_name":new_doc.customer_name,
				"note":note
			}
			)
			borrow_doc = frappe.get_cached_doc("Borrow Product",borrow_id)
			borrow_doc.add_comment('Info', note)
	# product remove
	for p in change_data.get("removed_products"):
		borrow_id = frappe.db.exists("Borrow Product",{"sale_product_id":p.get("name")})
		if borrow_id:
			borrow_doc = frappe.get_doc("Borrow Product",borrow_id)
			borrow_doc.flags.ignore_permissions = True
			borrow_doc.cancel()

	frappe.db.sql("update `tabBorrow Product` set posting_date = %(posting_date)s, customer=%(customer)s,customer_name=%(customer_name)s where reference_doctype ='Sale' and reference_name=%(name)s",{
		"posting_date":new_doc.posting_date,
		"customer":new_doc.customer,
		"customer_name":new_doc.customer_name,
		"name":new_doc.name,
	})

@frappe.whitelist()
def cancell_all_borrow_product(self):
	data = frappe.db.sql("select name from `tabBorrow Product` where reference_doctype='Sale' and reference_name=%(name)s",{"name":self.name},as_dict=1)
	for d in data:
		doc = frappe.get_doc("Borrow Product",d.get("name"))
		doc.flags.ignore_permissions = True
		doc.flags.force_cancel = True
		doc.cancel()

@frappe.whitelist(methods=["POST"])
def enable_edit_mode(doc_name: str, note: str):
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Reason for editing is required"))
	doc = frappe.get_doc("Sale", doc_name)
	doc.check_permission("write")
	if doc.sale_status != "Closed":
		frappe.throw(_("Only closed Sales can be put into edit mode"))
	doc.add_comment(
		"Info",
		_("Edit mode enabled. Reason: {0}").format(note),
	)
	return {"name": doc.name, "enable_edit_mode": 1}




def get_permission_query_conditions(user=None):
    user = user or frappe.session.user

    if user == "Administrator":
        return None

    access_outlets = get_current_employee_outlets()

    if not access_outlets:
        return "1 = 0"

    outlets = ", ".join(frappe.db.escape(outlet) for outlet in access_outlets)

    return f"tabSale.outlet IN ({outlets})"
	
