<script setup>
import { computed } from "vue";

import { navigate } from "../dashboard_utils";
import PanelShell from "./PanelShell.vue";
import TrendChart from "./TrendChart.vue";

const props = defineProps({
	data: { type: Object, default: () => ({ labels: [], income: [], expense: [], profit: [] }) },
	currency: { type: String, default: "" },
	routeOptions: { type: Object, default: null },
});

const datasets = computed(() => [
	{ name: "Revenue", values: props.data.income || [], color: "#2563eb", type: "bar" },
	{ name: "Expenses", values: props.data.expense || [], color: "#ef4444", type: "bar" },
	{ name: "Net Profit", values: props.data.profit || [], color: "#059669", type: "line" },
]);

function openProfitAndLoss() {
	navigate(["query-report", "Profit and Loss Statement"], props.routeOptions);
}
</script>

<template>
	<PanelShell title="Revenue, Expenses & Profit" subtitle="Performance during the selected period">
		<template #action>
			<button class="dashboard-text-button" type="button" @click="openProfitAndLoss">
				{{ __("View Report") }}
			</button>
		</template>
		<TrendChart
			:labels="data.labels || []"
			:datasets="datasets"
			:granularity="data.granularity"
			:currency="currency"
		/>
	</PanelShell>
</template>
