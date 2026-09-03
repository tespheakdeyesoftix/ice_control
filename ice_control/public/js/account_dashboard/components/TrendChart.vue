<script setup>
import { computed } from "vue";

import { formatChartLabel, formatCompactNumber, formatMoney, toNumber } from "../dashboard_utils";

const props = defineProps({
	labels: { type: Array, default: () => [] },
	datasets: { type: Array, default: () => [] },
	granularity: { type: String, default: "day" },
	currency: { type: String, default: "" },
});

const width = 720;
const height = 250;
const padding = { top: 18, right: 18, bottom: 42, left: 58 };
const plotWidth = width - padding.left - padding.right;
const plotHeight = height - padding.top - padding.bottom;

const values = computed(() => props.datasets.flatMap((dataset) => dataset.values || []).map(toNumber));
const domain = computed(() => {
	const minimum = Math.min(0, ...values.value);
	const maximum = Math.max(0, ...values.value);
	const span = maximum - minimum || 1;
	return { minimum: minimum - span * 0.08, maximum: maximum + span * 0.08 };
});
const step = computed(() => plotWidth / Math.max(props.labels.length, 1));
const barDatasets = computed(() => props.datasets.filter((dataset) => dataset.type !== "line"));
const gridValues = computed(() =>
	Array.from({ length: 5 }, (_, index) =>
		domain.value.minimum + ((domain.value.maximum - domain.value.minimum) * index) / 4
	).reverse()
);
const labelInterval = computed(() => Math.max(1, Math.ceil(props.labels.length / 7)));

function x(index) {
	return padding.left + step.value * index + step.value / 2;
}

function y(value) {
	return (
		padding.top +
		((domain.value.maximum - toNumber(value)) /
			(domain.value.maximum - domain.value.minimum || 1)) *
			plotHeight
	);
}

function barWidth() {
	return Math.max(3, Math.min(16, (step.value * 0.66) / Math.max(barDatasets.value.length, 1)));
}

function barX(dataset, index) {
	const datasetIndex = barDatasets.value.indexOf(dataset);
	const groupWidth = barWidth() * barDatasets.value.length;
	return x(index) - groupWidth / 2 + datasetIndex * barWidth();
}

function barY(value) {
	return Math.min(y(value), y(0));
}

function barHeight(value) {
	return Math.max(1, Math.abs(y(value) - y(0)));
}

function linePoints(dataset) {
	return (dataset.values || []).map((value, index) => `${x(index)},${y(value)}`).join(" ");
}
</script>

<template>
	<div class="trend-chart">
		<div class="trend-chart__legend">
			<span v-for="dataset in datasets" :key="dataset.name">
				<i :style="{ backgroundColor: dataset.color }"></i>{{ __(dataset.name) }}
			</span>
		</div>
		<div v-if="labels.length" class="trend-chart__canvas">
			<svg :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="__('Financial trend chart')">
				<g v-for="gridValue in gridValues" :key="gridValue">
					<line
						:stroke="'var(--dashboard-grid)'"
						:x1="padding.left"
						:x2="width - padding.right"
						:y1="y(gridValue)"
						:y2="y(gridValue)"
					/>
					<text class="trend-chart__axis" :x="padding.left - 8" :y="y(gridValue) + 4" text-anchor="end">
						{{ formatCompactNumber(gridValue, currency) }}
					</text>
				</g>

				<template v-for="dataset in datasets" :key="dataset.name">
					<polyline
						v-if="dataset.type === 'line'"
						:points="linePoints(dataset)"
						:stroke="dataset.color"
						fill="none"
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="3"
					/>
					<template v-else>
						<rect
							v-for="(value, index) in dataset.values"
							:key="`${dataset.name}-${index}`"
							:x="barX(dataset, index)"
							:y="barY(value)"
							:width="barWidth() - 1"
							:height="barHeight(value)"
							:fill="dataset.color"
							rx="2"
						>
							<title>{{ `${dataset.name}: ${formatMoney(value, currency)}` }}</title>
						</rect>
					</template>
				</template>

				<template v-for="(label, index) in labels" :key="label">
					<text
						v-if="index % labelInterval === 0 || index === labels.length - 1"
						class="trend-chart__axis"
						:x="x(index)"
						:y="height - 12"
						text-anchor="middle"
					>
						{{ formatChartLabel(label, granularity) }}
					</text>
				</template>
			</svg>
		</div>
		<div v-else class="dashboard-empty-state">{{ __("No chart data") }}</div>
	</div>
</template>
