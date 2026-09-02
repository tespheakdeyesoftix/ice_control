# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ProductCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.stock_management.doctype.product_category_default_accounts.product_category_default_accounts import ProductCategoryDefaultAccounts

		category_name: DF.Data
		enabled: DF.Check
		product_prefix: DF.Data | None
		revenue_group: DF.Link | None
		table_gdwo: DF.Table[ProductCategoryDefaultAccounts]
	# end: auto-generated types

	_DOCTYPE_NAME = "Product Category"
