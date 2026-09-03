<script setup>
import { computed } from "vue";

import PanelShell from "./PanelShell.vue";
import TrendChart from "./TrendChart.vue";

const props = defineProps({
	data: { type: Object, default: () => ({ labels: [], inflow: [], outflow: [] }) },
	currency: { type: String, default: "" },
});

const datasets = computed(() => [
	{ name: "Inflow", values: props.data.inflow || [], color: "#10b981", type: "bar" },
	{ name: "Outflow", values: props.data.outflow || [], color: "#ef4444", type: "bar" },
]);
</script>

<template>
	<PanelShell title="Cash Flow" subtitle="Operating cash inflow and outflow">
		<TrendChart
			:labels="data.labels || []"
			:datasets="datasets"
			:granularity="data.granularity"
			:currency="currency"
		/>
	</PanelShell>
</template>
