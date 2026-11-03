<script setup lang="ts">
import type { SetupIssue } from '../types'
defineProps<{ issues: SetupIssue[] }>()
</script>

<template>
  <section v-if="issues.length" class="card setup-alert">
    <h2>Требуется настройка</h2>
    <div v-for="issue in issues" :key="issue.code"><strong>{{ issue.message }}</strong><p>{{ issue.help }}</p></div>
    <p>Рабочие действия заблокированы до устранения этих проблем. Вход в hh.ru и VNC остаются доступны.</p>
  </section>
</template>
