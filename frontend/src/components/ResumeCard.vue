<script setup lang="ts">
import type { Resume } from '../types'

defineProps<{ resume: Resume; busy: boolean; browserSaved: boolean }>()
const emit = defineEmits<{
  togglePublishing: []
  toggleMonitoring: []
  publish: []
  ats: []
  collect: []
  history: []
  vacancies: []
  remove: []
}>()

const format = (value: string | null) => value ? new Date(value).toLocaleString('ru-RU') : '—'
</script>

<template>
  <article class="resume">
    <div class="resume-title"><h2>{{ resume.title }}</h2><small>ID: {{ resume.hh_resume_id }} · {{ resume.status || 'статус неизвестен' }}</small></div>
    <dl>
      <div><dt>Обновлено</dt><dd>{{ format(resume.published_at) }}</dd></div>
      <div><dt>Поднятие</dt><dd>{{ resume.publish_available === true ? 'доступно' : resume.publish_available === false ? 'пока недоступно' : 'ещё не проверено' }}</dd></div>
      <div><dt>ATS</dt><dd>{{ resume.ats_achievements === true ? 'конкретные достижения есть' : resume.ats_achievements === false ? 'конкретные достижения не найдены' : 'не проверено' }}</dd></div>
      <div><dt>Следующая публикация</dt><dd>{{ format(resume.next_publish_at) }}</dd></div>
      <div><dt>Вакансии проверены</dt><dd>{{ format(resume.last_vacancy_check_at) }}</dd></div>
      <div v-if="resume.last_error"><dt>Ошибка</dt><dd class="error">{{ resume.last_error }}</dd></div>
    </dl>
    <div class="resume-actions">
      <label><input :checked="resume.enabled" type="checkbox" @change="emit('togglePublishing')" /> Автообновление</label>
      <label><input :checked="resume.vacancy_monitoring_enabled" type="checkbox" @change="emit('toggleMonitoring')" /> Собирать вакансии (раз в час)</label>
      <button :disabled="busy" @click="emit('publish')">Обновить сейчас</button>
      <button :disabled="busy || !browserSaved" class="secondary" @click="emit('ats')">Проверить ATS</button>
      <button :disabled="busy || !browserSaved" class="secondary" @click="emit('collect')">Собрать вакансии</button>
      <button class="secondary" @click="emit('history')">История</button>
      <button class="secondary" @click="emit('vacancies')">Статистика подходящих вакансий</button>
      <button class="secondary" @click="emit('remove')">Убрать</button>
    </div>
  </article>
</template>
