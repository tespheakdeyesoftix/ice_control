<script setup>
defineProps({
	title: { type: String, required: true },
	subtitle: { type: String, default: "" },
});
</script>

<template>
	<section class="dashboard-panel">
		<header class="dashboard-panel__header">
			<div>
				<h2>{{ __(title) }}</h2>
				<p v-if="subtitle">{{ __(subtitle) }}</p>
			</div>
			<slot name="action"></slot>
		</header>
		<div class="dashboard-panel__body"><slot></slot></div>
	</section>
</template>
