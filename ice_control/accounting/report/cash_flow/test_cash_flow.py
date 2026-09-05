# Copyright (c) 2026, Tes Pheakdey and Contributors
# See license.txt

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import frappe

from ice_control.accounting.report.cash_flow.cash_flow import (
	build_rows,
	get_chart,
	normalize_selected_accounts,
)


class TestCashFlow(TestCase):
	def test_opening_balance_is_first_and_daily_balance_uses_both_flows(self):
		daily_flows = [
			frappe._dict(
				posting_date=date(2026, 9, 2),
				inflow=40,
				outflow=10,
			),
			frappe._dict(
				posting_date=date(2026, 9, 3),
				inflow=5,
				outflow=25,
			),
		]

		rows, totals = build_rows(
			date(2026, 9, 1), date(2026, 9, 3), 100, daily_flows
		)

		self.assertEqual(len(rows), 6)
		self.assertEqual(rows[0]["posting_date"], date(2026, 9, 1))
		self.assertEqual(rows[0]["is_opening"], 1)
		self.assertEqual(rows[0]["balance"], 100)
		self.assertIsNone(rows[0]["inflow"])
		self.assertIsNone(rows[0]["outflow"])
		self.assertEqual(rows[1]["posting_date"], date(2026, 9, 1))
		self.assertEqual(rows[1]["inflow"], 0)
		self.assertEqual(rows[1]["outflow"], 0)
		self.assertEqual(rows[1]["balance"], 100)
		self.assertEqual(rows[2]["inflow"], 40)
		self.assertEqual(rows[2]["outflow"], 10)
		self.assertEqual(rows[2]["balance"], 130)
		self.assertEqual(rows[3]["inflow"], 5)
		self.assertEqual(rows[3]["outflow"], 25)
		self.assertEqual(rows[3]["balance"], 110)
		self.assertEqual(rows[-2], {})
		self.assertEqual(rows[-1]["is_total"], 1)
		self.assertEqual(rows[-1]["inflow"], 45)
		self.assertEqual(rows[-1]["outflow"], 35)
		self.assertEqual(rows[-1]["balance"], 110)
		self.assertEqual(totals["total_inflow"], 45)
		self.assertEqual(totals["total_outflow"], 35)
		self.assertEqual(totals["closing_balance"], 110)

	@patch(
		"ice_control.accounting.report.cash_flow.cash_flow._",
		side_effect=lambda message: message,
	)
	def test_chart_uses_only_daily_rows(self, _mock_translate):
		rows, _totals = build_rows(
			date(2026, 9, 1),
			date(2026, 9, 3),
			100,
			[
				frappe._dict(
					posting_date=date(2026, 9, 2),
					inflow=40,
					outflow=10,
				)
			],
		)
		chart = get_chart(rows)

		self.assertEqual(
			chart["data"]["labels"],
			["2026-09-01", "2026-09-02", "2026-09-03"],
		)
		self.assertEqual(chart["data"]["datasets"][0]["values"], [0, 40, 0])
		self.assertEqual(chart["data"]["datasets"][1]["values"], [0, 10, 0])
		self.assertEqual(chart["type"], "bar")

	@patch(
		"ice_control.accounting.report.cash_flow.cash_flow._",
		side_effect=lambda message: message,
	)
	def test_chart_is_hidden_only_when_range_exceeds_31_days(self, _mock_translate):
		rows_31_days, _totals = build_rows(
			date(2026, 1, 1), date(2026, 1, 31), 0, []
		)
		rows_32_days, _totals = build_rows(
			date(2026, 1, 1), date(2026, 2, 1), 0, []
		)

		self.assertIsNotNone(get_chart(rows_31_days))
		self.assertIsNone(get_chart(rows_32_days))

	def test_empty_account_selection_means_all_accounts(self):
		self.assertEqual(normalize_selected_accounts(None), [])
		self.assertEqual(normalize_selected_accounts([]), [])

	def test_account_selection_is_normalized_and_deduplicated(self):
		self.assertEqual(
			normalize_selected_accounts(["Cash A", "Cash B", "Cash A", ""]),
			["Cash A", "Cash B"],
		)
		self.assertEqual(normalize_selected_accounts("Cash A"), ["Cash A"])
