<script setup lang="ts">
defineProps<{ rows: string[] }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <section v-if="rows.length" class="card history">
    <div class="section-heading"><h2>История операций</h2><button class="icon-button secondary" aria-label="Закрыть историю" @click="emit('close')">×</button></div>
    <p v-for="row in rows" :key="row">{{ row }}</p>
  </section>
</template>
