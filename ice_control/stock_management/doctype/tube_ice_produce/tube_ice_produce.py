# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TubeIceProduce(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from ice_control.stock_management.doctype.tube_ice_produce_machine.tube_ice_produce_machine import TubeIceProduceMachine

		amended_from: DF.Link | None
		naming_series: DF.Literal["TIP.YYYY.-.####"]
		note: DF.SmallText | None
		outlet: DF.Link | None
		posting_date: DF.Date
		total_end_meter_number: DF.Int
		total_infected_quantity: DF.Float
		total_produce_drop: DF.Float
		total_produce_quantity: DF.Float
		total_start_meter_number: DF.Int
		tube_ice_produce_quantity: DF.Table[TubeIceProduceMachine]
	# end: auto-generated types

	_DOCTYPE_NAME = "Tube Ice Produce"

	def before_insert(self):
		# Check that the child table has at least one row
		if not self.tube_ice_produce_quantity:
			return

		# Get the last Tube Ice Produce document
		last_docs = frappe.get_all(
			"Tube Ice Produce",
			filters={"docstatus": 1},
			fields=["name"],
			order_by="creation desc",
			limit_page_length=1  # only need the latest one
		)

		if last_docs:
			last_doc = frappe.get_doc("Tube Ice Produce", last_docs[0].name)

			if last_doc.tube_ice_produce_quantity:
				# Make a map of machine -> end_meter_number
				last_machines = {
					row.machine_name: row.end_meter_number
					for row in last_doc.tube_ice_produce_quantity
				}

				# Loop through current doc rows and set start_meter_number
				for row in self.tube_ice_produce_quantity:
					if row.machine_name in last_machines:
						row.start_meter_number = last_machines[row.machine_name]



	def validate(self):
		self.outlet = frappe.get_cached_value("Business Information",None,"tube_ice_outlet")
		self.total_produce_quantity = sum([d.total_produce_quantity or 0 for d in self.tube_ice_produce_quantity])
		self.total_produce_drop = sum([d.produce_drop or 0 for d in self.tube_ice_produce_quantity])
		self.total_infected_quantity = sum([d.infected_quantity or 0 for d in self.tube_ice_produce_quantity])
		self.total_start_meter_number = sum([d.start_meter_number or 0 for d in self.tube_ice_produce_quantity])
		self.total_end_meter_number = sum([d.end_meter_number or 0 for d in self.tube_ice_produce_quantity])

		#  New validation: end_meter_number must be >= start_meter_number
		for row in self.tube_ice_produce_quantity:
			if row.end_meter_number is not None and row.start_meter_number is not None:
				if row.end_meter_number < row.start_meter_number:
					frappe.throw(
						f"Row {row.idx}: End Meter Number ({row.end_meter_number}) "
						f"cannot be less than Start Meter Number ({row.start_meter_number})."
					)

	def before_submit(self):
		# frappe.throw("validate quantityy")
		pass


	# Custom doc method
	@frappe.whitelist()
	def get_tube_machine(self):

		sql ="select name,product_code,0 as start_meter_number, 1 as allow_edit_start_meter_number from `tabTube Ice Machine` order by sort_order"
		data = frappe.db.sql(sql,as_dict=1)
		for d in data:
			sql = "select  end_meter_number from `tabTube Ice Produce Machine` where machine_name = %(machine_name)s  and docstatus = 1  order by creation limit 1"
			meter_data = frappe.db.sql(sql,{"machine_name":d.get("name")},as_dict = 1)
			if meter_data:
				d["start_meter_number"] = meter_data[0].get("end_meter_number")
				d["allow_edit_start_meter_number"] = 1 if (meter_data[0].get("end_meter_number") or 0)==0 else 0



		return data
