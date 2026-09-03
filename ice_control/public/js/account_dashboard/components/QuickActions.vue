<script setup>
const actions = [
	{ label: "Receive Payment", doctype: "Sale Payment", icon: "arrow-down-left", theme: "green" },
	{ label: "Pay Vendor", doctype: "Purchase Order Payment", icon: "arrow-up-right", theme: "orange" },
	{ label: "Record Expense", doctype: "Expense", icon: "file-text", theme: "blue" },
	{ label: "Journal Entry", doctype: "Journal Entry", icon: "book-open", theme: "violet" },
];
</script>

<template>
	<section class="quick-actions" :aria-label="__('Quick actions')">
		<button
			v-for="action in actions"
			:key="action.doctype"
			class="quick-action"
			type="button"
			@click="frappe.new_doc(action.doctype)"
		>
			<span :class="`quick-action__icon is-${action.theme}`" v-html="frappe.utils.icon(action.icon, 'sm')"></span>
			<span>{{ __(action.label) }}</span>
			<span class="quick-action__arrow" v-html="frappe.utils.icon('chevron-right', 'xs')"></span>
		</button>
	</section>
</template>
