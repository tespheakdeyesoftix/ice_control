# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt


from frappe.utils import strip_html
from frappe.utils.password import update_password
import frappe
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
		change_customer: DF.Check
		change_product_price: DF.Check
		change_sale_date: DF.Check
		default_frontend_home_page: DF.Literal["/selling"]
		default_outlet: DF.Link
		delete_bill: DF.Check
		edit_bill: DF.Check
		employee_code: DF.Data | None
		employee_name: DF.Data | None
		enabled: DF.Check
		language: DF.Link | None
		naming_series: DF.Literal["EMP.####"]
		outlets: DF.Table[OutletChild]
		password: DF.Data | None
		phone_number: DF.Data | None
		photo: DF.AttachImage | None
		pos_payment: DF.Check
		position: DF.Link | None
		remove_sale_product: DF.Check
		role_profile: DF.Link | None
		split_bill: DF.Check
		user_id: DF.Data | None
		username: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Employee"

	def validate(self):
		if  strip_html(self.employee_code or ""):
			self.name = strip_html(self.employee_code or "")
		self._password = ""
		if self.password:
			self._password = self.password
			self.password = ""

	def on_update(self):
		if self.allow_login:
			email = "{}@mail.com".format(self.username.strip().lower().replace(" ", "_"))

			if not self.user_id:
				if frappe.db.exists("User", email):
					user_doc = frappe.get_doc("User", email)
				else:
					user_doc = frappe.new_doc("User")
					user_doc.email = email

				user_doc.first_name = self.employee_name
				user_doc.username = self.username
				user_doc.language = self.language
				user_doc.enabled = self.allow_login
				user_doc.set("role_profiles", [])

				if self.role_profile:
					user_doc.append("role_profiles", {"role_profile": self.role_profile})
					user_doc.module_profile = frappe.get_cached_value(
						"Role Profile", self.role_profile, "custom_module_profile"
					) or ""
				else:
					user_doc.set("roles", [])
					user_doc.module_profile = ""

				if user_doc.is_new():
					user_doc.insert(ignore_permissions=True)
				else:
					user_doc.save(ignore_permissions=True)

				self.user_id = user_doc.name

				if self._password:
					update_password(user=user_doc.name, pwd=self.get_password("_password"), logout_all_sessions=True)

			else:
				if check_user_field_changed(self, ["username", "employee_name", "language", "_password", "allow_login", "role_profile"]):
					user_doc = frappe.get_doc("User", self.user_id)
					user_doc.username = self.username
					user_doc.first_name = self.employee_name
					user_doc.language = self.language
					user_doc.enabled = self.allow_login
					user_doc.set("role_profiles", [])

					if self.role_profile:
						user_doc.append("role_profiles", {"role_profile": self.role_profile})
						user_doc.module_profile = frappe.get_cached_value(
							"Role Profile", self.role_profile, "custom_module_profile"
						) or ""
					else:
						user_doc.set("roles", [])
						user_doc.module_profile = ""

					if self._password:
						update_password(user=user_doc.name, pwd=self.get_password("_password"), logout_all_sessions=True)
					user_doc.save(ignore_permissions=True)

		else:
			if self.user_id:
				user_doc = frappe.get_doc("User", self.user_id)
				user_doc.enabled = False
				user_doc.save(ignore_permissions=True)

		update_outlet_user_permission(self)

	def on_trash(self):
		if(self.user_id):
			user_doc = frappe.get_doc("User", self.user_id)
			user_doc.delete(ignore_permissions=True)

def check_user_field_changed(self, fields):
	for f in fields:
		if self.has_value_changed(f):
			return True
	return False

def update_outlet_user_permission(self):
	frappe.db.sql("delete from `tabUser Permission` where user=%(user)s and allow = 'Outlet'",{"user":self.user_id})
	outlets = [self.default_outlet]
	outlets = set(outlets + [d.outlet for d in self.outlets])

	for o in outlets:
		user_permission_doc = frappe.new_doc("User Permission")
		user_permission_doc.user = self.user_id
		user_permission_doc.allow = "Outlet"
		user_permission_doc.for_value = o
		user_permission_doc.insert(ignore_permissions=True)


def get_permission_query_conditions(user):

	if not user:
		user = frappe.session.user
	if user=="Administrator":
		return None # not apply user permission


	query = f"""(`tabEmployee`.`name` not in ('Admin','admin','Administrator','administrator'))"""

	return query
