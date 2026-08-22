# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class Customer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.customer_management.doctype.customer_free_products.customer_free_products import CustomerFreeProducts
		from ice_control.customer_management.doctype.customer_product_price.customer_product_price import CustomerProductPrice

		address: DF.SmallText | None
		can_edit_bill: DF.Check
		can_show_price: DF.Check
		can_split_bill: DF.Check
		company_name: DF.Data | None
		customer_group: DF.Link
		customer_name: DF.Data
		enabled: DF.Check
		gender: DF.Literal["Male", "Female"]
		is_company: DF.Check
		is_customer: DF.Check
		is_driver: DF.Check
		keyword: DF.Data
		naming_series: DF.Literal["CU.####"]
		phone_number_1: DF.Data | None
		phone_number_2: DF.Data | None
		photo: DF.AttachImage | None
		plate_number: DF.Data | None
		product_prices: DF.Table[CustomerProductPrice]
		table_bvxf: DF.Table[CustomerFreeProducts]
	# end: auto-generated types

	_DOCTYPE_NAME = "Customer"


@frappe.whitelist()
def get_customer_product_price(
    customer: str = "",
    products: list[dict] | None = None,
    product_code: str = "",
    unit: str = "",
) -> dict:
	# if len(products) > 0:
	# 	products = json.loads(products)
	if products and len(products) > 0:
		base_product_prices = frappe.db.sql("select parent name,price,unit,multiplier from `tabProduct Units`",as_dict=1)
		customer_product_prices = frappe.db.sql("""SELECT product_code,price,unit,multiplier FROM `tabCustomer Product Price` WHERE parent = '{}'""".format(customer),as_dict=1)
		customer_free_products = frappe.db.sql("""SELECT product_code,quantity,unit,multiplier FROM `tabCustomer Free Products` WHERE parent = '{}'""".format(customer),as_dict=1)

		if len(base_product_prices)>0:
			for a in base_product_prices:
				for b in products:
					if (a.get("name") or "") != "" and ((a.get("name") or "") == b.get("product_code","")):
						if (a.get("unit","") == b.get("unit","")):
							b["price"] = a["price"]
							b["total_amount"] = b["price"] * b["total_sale_quantity"] * (a["multiplier"] or 1)
							b["multiplier"] = (a["multiplier"] or 1)
							b["sub_total"] = b["price"] * b["quantity"] * (a["multiplier"] or 1)
							b["__unsaved"] = 1
							b["__islocal"] = 1
						else:
							p = frappe.get_cached_doc("Product",b.get("product_code",""))
							m = frappe.get_cached_doc("Unit",b["unit"])
							b["price"] = p.price
							b["total_amount"] = b["price"] * b["total_sale_quantity"] *  (m.multiplier or 1)
							b["multiplier"] = (m.multiplier or 1)
							b["sub_total"] = b["price"] * b["quantity"] * (a["multiplier"] or 1)
							b["__unsaved"] = 1
							b["__islocal"] = 1


		if len(customer_product_prices)>0:
			for a in customer_product_prices:
				for b in products:
					if (a.get("product_code") or "") != "" and ((a.get("product_code") or "") == b.get("product_code","")) and (a.get("unit","") == b.get("unit","")):
						b["price"] = a["price"]
						b["total_amount"] = a["price"] * b["total_sale_quantity"]  * (a["multiplier"] or 1)
						b["multiplier"] = (a["multiplier"] or 1)
						b["sub_total"] = b["price"] * b["quantity"] * (a["multiplier"] or 1)
						b["__unsaved"] = 1
						b["__islocal"] = 1

		if len(customer_free_products)>0:
			for a in customer_free_products:
				for b in products:
					if (a.get("product_code") or "") != "" and (a.get("product_code") or "") == b.get("product_code",""):
						b["free_quantity"] = a["quantity"] * ((a["multiplier"] or 1) / (b["multiplier"] or 1))
						b["total_sale_quantity"] = b["quantity"] - (b["free_quantity"] * ((a["multiplier"] or 1) / (b["multiplier"] or 1)))
						b["total_amount"] = b["price"] * b["total_sale_quantity"]
						b["sub_total"] = b["price"] * b["quantity"]
		else:
			for a in products:
				a["free_quantity"] = 0
		return products
	else:
		multiplier = frappe.get_cached_doc("Unit",unit).multiplier
		if product_code:
			base_product_price = (frappe.db.sql("select parent name,price,unit,multiplier from `tabProduct Units` where parent = '{0}' and unit='{1}'".format(product_code,unit),as_dict=1) or [])
			if len(base_product_price) == 0:
				base_product_price = (frappe.db.sql("select parent name,price,unit,multiplier from `tabProduct Units` where parent = '{0}'".format(product_code),as_dict=1) or [])
			customer_product_prices = (frappe.db.sql("""SELECT product_code,price,multiplier FROM `tabCustomer Product Price` WHERE parent = '{0}' and product_code = '{1}' and unit = '{2}'""".format(customer,product_code,unit),as_dict=1) or [])
			customer_free_products = (frappe.db.sql("""SELECT product_code,quantity,unit,multiplier FROM `tabCustomer Free Products` WHERE parent = '{0}' and product_code = '{1}'""".format(customer,product_code),as_dict=1) or [])
			free_quantity = 0
			if len(customer_free_products)>0:
				free_multiplier = customer_free_products[0]["multiplier"] / multiplier
				free_quantity = (customer_free_products[0]["quantity"] or 0) * free_multiplier
			if len(customer_product_prices)>0:
				return {"price":customer_product_prices[0]["price"],"multiplier":multiplier,"free_quantity":free_quantity}
			else:
				return {"price":base_product_price[0]["price"],"multiplier":multiplier,"free_quantity":free_quantity}


@frappe.whitelist()
def get_events(start:str, end:str, filters:dict = None):
    events = frappe.get_all(
        "Sale",
        fields=[
            "name",
            "name as subject",
            "posting_date as start",
            "posting_date as end"
        ],
        filters={
            "posting_date": ["between", [frappe.utils.getdate(start), frappe.utils.getdate(end)]]
        }
    )
    frappe.msgprint(str(events))
    return events


@frappe.whitelist()
def get_customer_calendar_events(start: str, end: str, customer: str):
	if not customer:
		[]
	start_date = frappe.utils.getdate(start)
	end_date = frappe.utils.getdate(end)

	events = []

	sales = frappe.db.sql(
        """
        SELECT
            name AS id,
            'Sale' AS doctype,
            name AS title,
            posting_date AS start,
            posting_date AS end,
            customer,
            customer_name,
            total_amount,
            balance,
            'blue' AS color
        FROM `tabSale`
        WHERE
            customer = %(customer)s
            AND posting_date BETWEEN %(start_date)s AND %(end_date)s
            AND docstatus != 2
        ORDER BY posting_date
        """,
        {
            "customer": customer,
            "start_date": start_date,
            "end_date": end_date,
        },
        as_dict=True,
    )

	events.extend(sales)

	payments = frappe.db.sql(
		"""
		SELECT
			name AS id,
			'Sale Payment' AS doctype,
			name AS title,
			posting_date AS start,
			posting_date AS end,
			customer,
			customer_name,
			payment_amount,
			'green' AS color
		FROM `tabSale Payment`
		WHERE
			customer = %(customer)s
			AND posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND docstatus != 2
		ORDER BY posting_date
		""",
		{
			"customer": customer,
			"start_date": start_date,
			"end_date": end_date,
		},
		as_dict=True,
	)

	events.extend(payments)

	# Sort all events by date
	events.sort(key=lambda x: str(x.get("start") or ""))

	return events

