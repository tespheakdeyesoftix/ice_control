from datetime import date

import frappe
from frappe.tests import UnitTestCase

from ice_control.accounting.page.account_dashboard.account_dashboard import (
	_build_payable_aging,
	_build_receivable_aging,
	_build_summary,
	_build_trends,
	_get_aging_bucket,
	_percentage_change,
)


class TestAccountDashboard(UnitTestCase):
	def test_percentage_change_handles_zero_comparison(self):
		self.assertIsNone(_percentage_change(0, 0))
		self.assertEqual(_percentage_change(25, 0), 100)
		self.assertEqual(_percentage_change(75, 50), 50)

	def test_summary_marks_lower_receivable_and_payable_as_positive(self):
		summary = _build_summary(
			{"cash_and_bank": 120, "receivable": 80, "payable": 40},
			{"cash_and_bank": 100, "receivable": 100, "payable": 50},
			{
				"profit": 30,
				"total_sales": 100,
				"collections": 90,
				"purchase_payments": 20,
				"expense": 40,
				"net_cash_movement": 70,
			},
			{
				"profit": 20,
				"total_sales": 80,
				"collections": 70,
				"purchase_payments": 30,
				"expense": 50,
			},
		)

		self.assertTrue(summary["cash_and_bank"]["is_positive"])
		self.assertTrue(summary["receivable"]["is_positive"])
		self.assertTrue(summary["payable"]["is_positive"])
		self.assertEqual(summary["net_cash_movement"], 70)

	def test_daily_trends_fill_dates_without_activity(self):
		rows = [
			frappe._dict(
				posting_date=date(2026, 9, 2),
				income=100,
				expense=35,
				inflow=80,
				outflow=20,
			)
		]

		financial, cash_flow = _build_trends(rows, date(2026, 9, 1), date(2026, 9, 3))

		self.assertEqual(financial["labels"], ["2026-09-01", "2026-09-02", "2026-09-03"])
		self.assertEqual(financial["income"], [0, 100, 0])
		self.assertEqual(financial["profit"], [0, 65, 0])
		self.assertEqual(cash_flow["net"], [0, 60, 0])

	def test_receivable_aging_applies_credits_fifo(self):
		rows = [
			frappe._dict(party="CUST-1", posting_date=date(2026, 1, 1), debit_amount=100, credit_amount=0),
			frappe._dict(party="CUST-1", posting_date=date(2026, 1, 20), debit_amount=50, credit_amount=0),
			frappe._dict(party="CUST-1", posting_date=date(2026, 2, 5), debit_amount=0, credit_amount=80),
			frappe._dict(party="CUST-2", posting_date=date(2026, 2, 5), debit_amount=0, credit_amount=25),
		]

		aging, overdue_customers = _build_receivable_aging(rows, date(2026, 4, 15))
		amounts = {row["key"]: row["value"] for row in aging}

		self.assertEqual(amounts["days_61_90"], 50)
		self.assertEqual(amounts["days_91_120"], 20)
		self.assertEqual(overdue_customers, {"CUST-1"})

	def test_payable_aging_applies_debits_fifo(self):
		rows = [
			frappe._dict(
				party_type="Vendor",
				party="VENDOR-1",
				posting_date=date(2026, 1, 1),
				debit_amount=0,
				credit_amount=100,
			),
			frappe._dict(
				party_type="Vendor",
				party="VENDOR-1",
				posting_date=date(2026, 1, 20),
				debit_amount=0,
				credit_amount=50,
			),
			frappe._dict(
				party_type="Vendor",
				party="VENDOR-1",
				posting_date=date(2026, 2, 5),
				debit_amount=80,
				credit_amount=0,
			),
		]

		aging = _build_payable_aging(rows, date(2026, 4, 15))
		amounts = {row["key"]: row["value"] for row in aging}

		self.assertEqual(amounts["days_61_90"], 50)
		self.assertEqual(amounts["days_91_120"], 20)

	def test_aging_bucket_boundaries(self):
		self.assertEqual(_get_aging_bucket(0), "current")
		self.assertEqual(_get_aging_bucket(30), "days_1_30")
		self.assertEqual(_get_aging_bucket(60), "days_31_60")
		self.assertEqual(_get_aging_bucket(90), "days_61_90")
		self.assertEqual(_get_aging_bucket(91), "days_91_120")
		self.assertEqual(_get_aging_bucket(120), "days_91_120")
		self.assertEqual(_get_aging_bucket(121), "days_over_120")
