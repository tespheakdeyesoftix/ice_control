# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Employee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.setting.doctype.outlet_child.outlet_child import OutletChild

		address: DF.Data | None
		allow_login: DF.Check
		default_frontend_home_page: DF.Literal["/selling"]
		default_outlet: DF.Link
		employee_code: DF.Data | None
		employee_name: DF.Data | None
		language: DF.Link | None
		naming_series: DF.Literal[None]
		outlets: DF.Table[OutletChild]
		password: DF.Data | None
		phone_number: DF.Data | None
		photo: DF.AttachImage | None
		role_profile: DF.Link | None
		user_id: DF.Data | None
		username: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Employee"
