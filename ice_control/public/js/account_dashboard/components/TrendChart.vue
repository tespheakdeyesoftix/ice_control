<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import { formatChartLabel, formatCompactNumber, formatMoney, toNumber } from "../dashboard_utils";

const props = defineProps({
	labels: { type: Array, default: () => [] },
	datasets: { type: Array, default: () => [] },
	granularity: { type: String, default: "day" },
	currency: { type: String, default: "" },
});

const chartRoot = ref(null);

let chart = null;
let activeChartType = "";
let renderVersion = 0;

const normalizedLabels = computed(() =>
	props.labels.map((label) => formatChartLabel(label, props.granularity))
);
const normalizedDatasets = computed(() =>
	props.datasets.map((dataset) => ({
		name: __(dataset.name),
		values: (dataset.values || []).map(toNumber),
		chartType: dataset.type === "line" ? "line" : "bar",
	}))
);
const hasData = computed(
	() =>
		normalizedLabels.value.length > 0 &&
		normalizedDatasets.value.some((dataset) => dataset.values.some((value) => value !== 0))
);
const chartType = computed(() => {
	const types = new Set(normalizedDatasets.value.map((dataset) => dataset.chartType));
	return types.size > 1 ? "axis-mixed" : [...types][0] || "bar";
});

function getChartData() {
	return {
		labels: normalizedLabels.value,
		datasets: normalizedDatasets.value,
	};
}

function destroyChart() {
	chart?.destroy?.();
	chart = null;
	activeChartType = "";
	chartRoot.value?.replaceChildren();
}

async function renderChart() {
	const currentVersion = ++renderVersion;
	await nextTick();
	if (currentVersion !== renderVersion) return;

	if (!chartRoot.value || !hasData.value) {
		destroyChart();
		return;
	}

	const nextChartData = getChartData();
	if (chart && activeChartType === chartType.value) {
		chart.update(nextChartData);
		return;
	}

	destroyChart();
	activeChartType = chartType.value;
	chart = new frappe.Chart(chartRoot.value, {
		data: nextChartData,
		type: activeChartType,
		height: 280,
		colors: props.datasets.map((dataset) => dataset.color),
		animate: 0,
		truncateLegends: 0,
		axisOptions: {
			xIsSeries: 1,
			xAxisMode: "tick",
			shortenYAxisNumbers: 1,
			numberFormatter: (value) => formatCompactNumber(value, props.currency),
		},
		barOptions: {
			spaceRatio: 0.35,
			stacked: 0,
		},
		lineOptions: {
			dotSize: 5,
			showDots: 1,
			regionFill: 0,
		},
		tooltipOptions: {
			formatTooltipX: (label) => label,
			formatTooltipY: (value) => formatMoney(value, props.currency),
		},
	});

	// Frappe Charts starts with zeroed data before its delayed first draw.
	// Updating immediately keeps every mixed-series layer visible from the start.
	chart.update(nextChartData);
}

watch(
	() => [props.labels, props.datasets, props.granularity, props.currency],
	renderChart,
	{ deep: true, immediate: true }
);

onBeforeUnmount(() => {
	renderVersion += 1;
	destroyChart();
});
</script>

<template>
	<div class="trend-chart">
		<div v-show="hasData" ref="chartRoot" class="trend-chart__canvas frappe-chart-host"></div>
		<div v-if="!hasData" class="dashboard-empty-state">
			{{ __("No financial activity in the selected period") }}
		</div>
	</div>
</template>
