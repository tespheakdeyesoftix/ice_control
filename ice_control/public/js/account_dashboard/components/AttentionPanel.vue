<script setup>
import { navigate } from "../dashboard_utils";
import PanelShell from "./PanelShell.vue";

defineProps({ items: { type: Array, default: () => [] } });
</script>

<template>
	<PanelShell title="Attention Required" subtitle="Items that may need accounting review">
		<div v-if="items.length" class="attention-list">
			<button
				v-for="item in items"
				:key="item.key"
				class="attention-item"
				type="button"
				@click="navigate(item.route, item.route_options)"
			>
				<span class="attention-item__dot" :class="`is-${item.severity}`"></span>
				<span class="attention-item__content">
					<strong>{{ item.title }}</strong>
					<small>{{ item.message }}</small>
				</span>
				<span class="attention-item__arrow" v-html="frappe.utils.icon('chevron-right', 'sm')"></span>
			</button>
		</div>
		<div v-else class="dashboard-empty-state dashboard-empty-state--success">
			<span v-html="frappe.utils.icon('check-circle', 'md')"></span>
			{{ __("No accounting issues found for this period.") }}
		</div>
	</PanelShell>
</template>
