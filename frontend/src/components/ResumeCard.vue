<script setup lang="ts">
import type { Resume } from '../types'
import { formatDateTime } from '../utils/date'

const props = defineProps<{ resume: Resume; busy: boolean; browserSaved: boolean }>()
const emit = defineEmits<{
  togglePublishing: []
  toggleMonitoring: []
  toggleResponseLimit: []
  setResponseLimit: [limit: number]
  publish: []
  ats: []
  collect: []
  history: []
  vacancies: []
  remove: []
}>()

function setResponseLimit(event: Event) {
  const limit = Number((event.target as HTMLInputElement).value)
  if (Number.isInteger(limit) && limit > 0) emit('setResponseLimit', limit)
}
</script>

<template>
  <article class="resume">
    <div class="resume-title"><h2>{{ resume.title }}</h2><small>ID: {{ resume.hh_resume_id }} · {{ resume.status || 'статус неизвестен' }}</small></div>
    <dl>
      <div><dt>Обновлено</dt><dd>{{ formatDateTime(resume.published_at) }}</dd></div>
      <div><dt>Поднятие</dt><dd>{{ resume.publish_available === true ? 'доступно' : resume.publish_available === false ? 'пока недоступно' : 'ещё не проверено' }}</dd></div>
      <div><dt>ATS</dt><dd>{{ resume.ats_achievements === true ? 'конкретные достижения есть' : resume.ats_achievements === false ? 'конкретные достижения не найдены' : 'не проверено' }}</dd></div>
      <div><dt>Следующая публикация</dt><dd>{{ formatDateTime(resume.next_publish_at) }}</dd></div>
      <div><dt>Вакансии проверены</dt><dd>{{ formatDateTime(resume.last_vacancy_check_at) }}</dd></div>
      <div v-if="resume.last_error"><dt>Ошибка</dt><dd class="error">{{ resume.last_error }}</dd></div>
    </dl>
    <div class="resume-actions">
      <label><input :checked="resume.enabled" type="checkbox" @change="emit('togglePublishing')" /> Автообновление</label>
      <label><input :checked="resume.vacancy_monitoring_enabled" type="checkbox" @change="emit('toggleMonitoring')" /> Собирать вакансии (раз в час)</label>
      <label v-if="resume.vacancy_monitoring_enabled"><input :checked="resume.vacancy_response_limit_enabled" type="checkbox" @change="emit('toggleResponseLimit')" /> Собирать только вакансии с откликами менее</label>
      <label v-if="resume.vacancy_monitoring_enabled && resume.vacancy_response_limit_enabled" class="response-limit">
        <span>Лимит откликов</span>
        <input :value="props.resume.vacancy_response_limit" type="number" min="1" step="1" inputmode="numeric" @change="setResponseLimit" />
      </label>
      <button :disabled="busy" @click="emit('publish')">Обновить сейчас</button>
      <button :disabled="busy || !browserSaved" class="secondary" @click="emit('ats')">Проверить ATS</button>
      <button :disabled="busy || !browserSaved" class="secondary" @click="emit('collect')">Собрать вакансии</button>
      <button class="secondary" @click="emit('history')">История</button>
      <button class="secondary" @click="emit('vacancies')">Статистика подходящих вакансий</button>
      <button class="secondary" @click="emit('remove')">Убрать</button>
    </div>
  </article>
</template>
