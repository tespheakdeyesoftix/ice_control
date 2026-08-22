# Copyright (c) 2025, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters) -> list[dict]:
	columns =  [
		{
			"label": _("ID"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options":"Customer",
			"width":75
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width":250
		},
		{
			"label": _("Phone Number"),
			"fieldname": "phone_number",
			"fieldtype": "Data",
			"width":150,
			"align":"left"
		},
		{
			"label": _("Customer Group"),
			"fieldname": "customer_group",
			"fieldtype": "Data",
			"width":150
		},
	]

	# get dynamic column from tbl_product

	sql = "select name as fieldname, product_name as label, 'Currency' as fieldtype from `tabProduct` where show_in_customer_product_price=1 "
	if filters.product_category:
		sql = sql + " and product_category=%(product_category)s"
	sql = sql + "order by sort_order,product_category"
	
	data = frappe.db.sql(sql,filters,as_dict = 1)
	columns = columns + data


	return columns


def get_data(filters) -> list[list]:
	
	sql = "select name as customer, customer_name as customer_name,customer_group,phone_number_1 as phone_number from `tabCustomer` where true "
	if filters.customer_group:
		sql = sql + " and customer_group=%(customer_group)s"
		
	if filters.customer:
		sql = sql + " and name=%(customer)s"

	sql = sql + " order by name, customer_name"
	customer_list = frappe.db.sql(sql,filters,as_dict = 1)
	# get customer product price
	sql = """select pp.parent as customer,  pp.product_code, pp.product_name, pp.price 
		from `tabCustomer Product Price` pp 
			inner join `tabProduct` p on p.name = pp.product_code 
			inner join `tabCustomer` c on c.name = pp.parent	
		where true 
		"""
	

	if filters.prouct_category:
		sql = sql + " and p.product_category = %(product_category)s"
	if filters.customer_group:
		sql = sql + " and  c.customer_group = %(customer_group)s"
	if filters.customer:
		sql = sql + " and  c.name = %(customer)s"
	
	
	
	prices  =  frappe.db.sql(sql,filters,as_dict=1)
	for p in prices:
		customer = next((r for r in customer_list if r.get("customer") == p.get("customer")), None)
		if customer:
			customer[p.product_code] = p.get("price")
	return customer_list
