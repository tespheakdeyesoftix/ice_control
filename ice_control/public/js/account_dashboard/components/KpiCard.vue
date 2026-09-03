<script setup>
import { computed } from "vue";

import { formatMoney, navigate } from "../dashboard_utils";

const props = defineProps({
	label: { type: String, required: true },
	metric: { type: Object, default: () => ({ value: 0 }) },
	currency: { type: String, default: "" },
	icon: { type: String, default: "dollar-sign" },
	theme: { type: String, default: "blue" },
	route: { type: Array, default: null },
	routeOptions: { type: Object, default: null },
});

const changeLabel = computed(() => {
	if (props.metric?.change === null || props.metric?.change === undefined) {
		return __("No comparison");
	}
	return `${props.metric.change >= 0 ? "+" : ""}${props.metric.change}%`;
});
</script>

<template>
	<button
		class="kpi-card"
		:class="[`kpi-card--${theme}`, { 'kpi-card--clickable': route }]"
		type="button"
		:disabled="!route"
		@click="navigate(route, routeOptions)"
	>
		<span class="kpi-card__icon" v-html="frappe.utils.icon(icon, 'md')"></span>
		<span class="kpi-card__content">
			<span class="kpi-card__label">{{ __(label) }}</span>
			<strong class="kpi-card__value">{{ formatMoney(metric?.value, currency) }}</strong>
			<span
				class="kpi-card__change"
				:class="{
					'is-positive': metric?.is_positive === true,
					'is-negative': metric?.is_positive === false,
				}"
			>
				{{ changeLabel }}
				<small>{{ __("vs previous period") }}</small>
			</span>
		</span>
	</button>
</template>
