<script setup>
import { computed, onMounted, reactive } from "vue";

import AttentionPanel from "./components/AttentionPanel.vue";
import CashFlowPanel from "./components/CashFlowPanel.vue";
import CompactMetric from "./components/CompactMetric.vue";
import DashboardFilters from "./components/DashboardFilters.vue";
import FinancialTrendPanel from "./components/FinancialTrendPanel.vue";
import KpiCard from "./components/KpiCard.vue";
import QuickActions from "./components/QuickActions.vue";
import PayableAging from "./components/PayableAging.vue";
import ReceivableAging from "./components/ReceivableAging.vue";
import RecentTransactions from "./components/RecentTransactions.vue";
import TopPayables from "./components/TopPayables.vue";
import TopReceivables from "./components/TopReceivables.vue";
import { useDashboardData } from "./composables/useDashboardData";
import { formatMoney } from "./dashboard_utils";

const props = defineProps({ initialOutlet: { type: String, default: "" } });
const filters = reactive({
	outlet: props.initialOutlet,
	start_date: frappe.datetime.month_start(),
	end_date: frappe.datetime.get_today(),
});
const { data, loading, error, load } = useDashboardData();

const currency = computed(() => data.value?.currency || frappe.defaults.get_default("currency") || "");
const summary = computed(() => data.value?.summary || {});
const reportOptions = computed(() => ({
	start_date: filters.start_date,
	end_date: filters.end_date,
	...(filters.outlet ? { outlet: filters.outlet } : {}),
}));

const listFilterOptions = computed(() => ({
	posting_date: ["between", [filters.start_date, filters.end_date]],
	...(filters.outlet ? { outlet: filters.outlet } : {}),
}));

const kpiCards = computed(() => [
	{
		key: "cash_and_bank",
		label: "Cash & Bank",
		icon: "landmark",
		theme: "green",
		route: ["query-report", "General Ledger"],
	},
	{
		key: "receivable",
		label: "Receivable",
		icon: "users",
		theme: "blue",
		route: ["query-report", "Account Receivable"],
	},
	{
		key: "payable",
		label: "Payable",
		icon: "wallet",
		theme: "orange",
		route: ["query-report", "Account Payable"],
	},
	{
		key: "net_profit",
		label: "Net Profit",
		icon: "trending-up",
		theme: "violet",
		route: ["query-report", "Profit and Loss Statement"],
	},
]);

const compactMetrics = computed(() => [
	{ key: "total_sales", label: "Total Sales", icon: "shopping-cart", theme: "blue", route: ["List", "Sale"] },
	{ key: "collections", label: "Collections", icon: "arrow-down-left", theme: "green", route: ["List", "Sale Payment"] },
	{
		key: "purchase_payments",
		label: "Purchase Payments",
		icon: "arrow-up-right",
		theme: "orange",
		route: ["List", "Purchase Order Payment"],
	},
	{ key: "expenses", label: "Expenses", icon: "chart-pie", theme: "violet", route: ["List", "Expense"] },
]);

async function refresh(nextFilters = null) {
	if (nextFilters) Object.assign(filters, nextFilters);
	try {
		const response = await load(filters);
		if (response?.filters) Object.assign(filters, response.filters);
	} catch (exception) {
		console.error("Unable to load Account Dashboard", exception);
	}
}

function openCashFlow() {
	frappe.route_options = {
		outlet: filters.outlet || "",
		start_date: filters.start_date,
		end_date: filters.end_date,
	};
	frappe.set_route("query-report", "Cash Flow");
}

defineExpose({ refresh });
onMounted(refresh);
</script>

<template>
	<main class="account-dashboard">
		<header class="account-dashboard__intro" >
			<div>

				<p class="account-dashboard__eyebrow">{{ __("Accounting") }}</p>
				<h1>{{ __("Financial overview and daily control") }}</h1>
				<p>{{ __("Posted balances, cash movement, aging and exceptions in one place.") }}</p>
			</div>
			<button v-if="data" class="cash-movement" type="button" @click="openCashFlow">
				<span>{{ __("Net Cash Movement") }}</span>
				<strong>{{ formatMoney(summary.net_cash_movement, currency) }}</strong>
			</button>
		</header>

		<DashboardFilters
			:model-value="filters"
			:outlets="data?.outlets || []"
			:loading="loading"
			@apply="refresh"
		/>

		<div v-if="error" class="dashboard-error" role="alert">
			<span v-html="frappe.utils.icon('alert-triangle', 'sm')"></span>
			<div><strong>{{ __("Dashboard could not be loaded") }}</strong><p>{{ error }}</p></div>
			<button type="button" @click="refresh()">{{ __("Try Again") }}</button>
		</div>

		<div v-if="loading && !data" class="dashboard-skeleton" :aria-label="__('Loading dashboard')">
			<span v-for="index in 12" :key="index"></span>
		</div>

		<template v-else-if="data">
			<section class="kpi-grid">
				<KpiCard
					v-for="card in kpiCards"
					:key="card.key"
					:label="card.label"
					:metric="summary[card.key]"
					:currency="currency"
					:icon="card.icon"
					:theme="card.theme"
					:route="card.route"
					:route-options="reportOptions"
				/>
			</section>

			<section class="compact-metric-grid">
				<CompactMetric
					v-for="metric in compactMetrics"
					:key="metric.key"
					:label="metric.label"
					:metric="summary[metric.key]"
					:currency="currency"
					:icon="metric.icon"
					:theme="metric.theme"
					:route="metric.route"
					:route-options="listFilterOptions"
				/>
			</section>

			<section class="dashboard-grid dashboard-grid--primary">
				<FinancialTrendPanel :data="data.financial_trend" :currency="currency" :route-options="reportOptions" />
				<AttentionPanel :items="data.alerts" />
			</section>

			<section class="dashboard-grid dashboard-grid--secondary">
				<ReceivableAging :rows="data.receivable_aging" :currency="currency" :route-options="reportOptions" />
				<TopReceivables :rows="data.top_receivables" :currency="currency" :route-options="reportOptions" />
			</section>

			<section class="dashboard-grid dashboard-grid--secondary">
				<PayableAging :rows="data.payable_aging" :currency="currency" :route-options="reportOptions" />
				<TopPayables :rows="data.top_payables" :currency="currency" :route-options="reportOptions" />
			</section>

			<section class="dashboard-grid dashboard-grid--cash-flow">
				<CashFlowPanel
					:data="data.cash_flow"
					:currency="currency"
					@view-report="openCashFlow"
				/>
			</section>

			<section class="dashboard-grid dashboard-grid--bottom">
				<RecentTransactions :rows="data.recent_transactions" :currency="currency" />
				<QuickActions />
			</section>

			<footer class="account-dashboard__footer">
				{{ __("Last refreshed") }}:
				{{ frappe.datetime.str_to_user(data.generated_at?.slice(0, 10)) }}
			</footer>
		</template>
	</main>
</template>
