<script setup>
import { formatMoney } from "../dashboard_utils";

defineProps({
	label: { type: String, required: true },
	metric: { type: Object, default: () => ({ value: 0 }) },
	currency: { type: String, default: "" },
	icon: { type: String, default: "bar-chart-2" },
	theme: { type: String, default: "blue" },
});
</script>

<template>
	<div class="compact-metric" :class="`compact-metric--${theme}`">
		<span class="compact-metric__icon" v-html="frappe.utils.icon(icon, 'sm')"></span>
		<span>
			<span class="compact-metric__label">{{ __(label) }}</span>
			<strong>{{ formatMoney(metric?.value, currency) }}</strong>
		</span>
	</div>
</template>
