# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet


class SystemReport(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		default_filter_options: DF.JSON | None
		description: DF.SmallText | None
		doctype_name: DF.Link | None
		is_backend_report: DF.Check
		is_doctype_report: DF.Check
		is_group: DF.Check
		is_seller_report: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		parent_system_report: DF.Link | None
		report_title: DF.Data | None
		report_url: DF.Data | None
		rgt: DF.Int
		roles: DF.Table[HasRole]
		show_in_report_list: DF.Check
		sort_order: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "System Report"
