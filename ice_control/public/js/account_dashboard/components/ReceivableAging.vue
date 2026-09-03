<script setup>
import { computed } from "vue";

import { formatMoney, toNumber } from "../dashboard_utils";
import PanelShell from "./PanelShell.vue";

const props = defineProps({
	rows: { type: Array, default: () => [] },
	currency: { type: String, default: "" },
});

const maximum = computed(() => Math.max(1, ...props.rows.map((row) => toNumber(row.value))));
const colors = ["#10b981", "#3b82f6", "#f59e0b", "#f97316", "#ef4444"];
</script>

<template>
	<PanelShell title="Receivable Aging" subtitle="Outstanding customer balances by age">
		<div class="aging-list">
			<div v-for="(row, index) in rows" :key="row.key" class="aging-row">
				<span class="aging-row__label">{{ row.label }}</span>
				<div class="aging-row__track">
					<span
						class="aging-row__bar"
						:style="{
							width: `${Math.max(2, (toNumber(row.value) / maximum) * 100)}%`,
							backgroundColor: colors[index],
						}"
					></span>
				</div>
				<strong>{{ formatMoney(row.value, currency) }}</strong>
			</div>
		</div>
	</PanelShell>
</template>
