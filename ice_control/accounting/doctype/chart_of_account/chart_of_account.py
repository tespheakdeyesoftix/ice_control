# Copyright (c) 2026, Tes Pheakdey and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.nestedset import NestedSet
from functools import lru_cache
from frappe import _

class ChartofAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_code: DF.Data | None
		account_name: DF.Data
		account_type: DF.Literal["", "Receivable", "Payable", "Cash", "Bank", "Income", "Expense", "Equity", "Owner Withdraw", "Temporary", "Stock Asset", "Fixed Asset"]
		descriptions: DF.SmallText | None
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		outlet: DF.Data | None
		parent_chart_of_account: DF.Link | None
		rgt: DF.Int
		root_type: DF.Literal["Asset", "Liabilities", "Equity", "Income", "Expenses"]
	# end: auto-generated types

	_DOCTYPE_NAME = "Chart of Account"

	def autoname(self):
		self.name ="{}-{}".format((self.account_code).strip(),(self.account_name).strip() )

@lru_cache(maxsize=128)
def  get_hierarchy_account_for_report_by_parent(parent):
    sql="""
        WITH RECURSIVE hierarchy AS (
            SELECT
                name as account,
                parent_chart_of_account,
                0 AS indent,
                CAST(account_code AS CHAR(255)) AS path
            FROM
                `tabChart of Account`
            WHERE
                name = %(parent)s
            UNION ALL
            SELECT
                t.name as account,
                t.parent_chart_of_account,
                h.indent + 1 AS indent,
                CONCAT(h.path, '-', t.account_code) AS path
            FROM
                `tabChart of Account` t
            JOIN
                hierarchy h ON t.parent_chart_of_account = h.account
        )
        SELECT
            account,
            parent_chart_of_account,
            indent
        FROM
            hierarchy
        ORDER BY
            path;

    """
    return frappe.db.sql(sql,{"parent":parent},as_dict=1)

def get_timespan_report_column(filters):
	column_info =  get_column_group_info(filters.column_group)
	filters = get_filter_date_range(filters)

	sql="""
		select
			{1} as name,
			{0}
		from `tabDates`
		where
			date between %(start_date)s and %(end_date)s
		group by
			{1}
		order by date
	""".format(column_info["sql_expression"],column_info["group_by_expression"])
	data = frappe.db.sql(sql,filters,as_dict=1)
	if len(data)>24:
		frappe.throw(_("Report column must be less than 24 columns"))
	return data

def get_column_group_info(key):
    return [d for d in column_group_keys() if d["key"] == key][0]

def column_group_keys():
    return [
        {"key":"Yearly","sql_expression":"date_format(date,'%%Y') as column_group", "group_by_expression":"date_format(date,'%%Y')" },
        {"key":"Monthly","sql_expression":"date_format(date,'%%b %%y') as column_group", "group_by_expression":"date_format(date,'%%b %%y')" },
        {"key":"Quarterly","sql_expression":"concat(date_format(min(date),'%%b %%y'),'-',date_format(max(date),'%%b %%y')) as column_group", "group_by_expression":"concat(QUARTER(date),'-', date_format(date,'%%Y'))" },
        {"key":"Half-Yearly","sql_expression":"concat(date_format(min(date),'%%b %%y'),'-',date_format(max(date),'%%b %%y')) as column_group", "group_by_expression":"concat(floor((month(date)-1)/6),'-', date_format(date,'%%Y'))" },
    ]

def get_filter_date_range(filters):
    if filters.filter_based_on =='Fiscal Year':
        filters.start_date =  '{}-01-01'.format(filters.start_year)
        filters.end_date =  '{}-12-31'.format(filters.end_year)
    return filters
