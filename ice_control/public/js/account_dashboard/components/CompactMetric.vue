<script setup>
import { formatMoney, navigate } from "../dashboard_utils";

defineProps({
	label: { type: String, required: true },
	metric: { type: Object, default: () => ({ value: 0 }) },
	currency: { type: String, default: "" },
	icon: { type: String, default: "shopping-cart" },
	theme: { type: String, default: "blue" },
	route: { type: Array, default: null },
	routeOptions: { type: Object, default: null },
});
</script>

<template>
	<button
		class="compact-metric"
		:class="[`compact-metric--${theme}`, { 'compact-metric--clickable': route }]"
		type="button"
		:disabled="!route"
		@click="navigate(route, routeOptions)"
	>
		<span class="compact-metric__icon" v-html="frappe.utils.icon(icon, 'sm')"></span>
		<span>
			<span class="compact-metric__label">{{ __(label) }}</span>
			<strong>{{ formatMoney(metric?.value, currency) }}</strong>
		</span>
	</button>
</template>
