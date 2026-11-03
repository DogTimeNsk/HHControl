<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ busy: boolean }>()
const emit = defineEmits<{ close: []; submit: [id: string] }>()
const resumeId = ref('')
function submit() { emit('submit', resumeId.value) }
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <form class="modal card" @submit.prevent="submit">
      <h2>Добавить резюме вручную</h2><p>Скопируйте ID из адреса страницы резюме на hh.ru.</p>
      <input v-model.trim="resumeId" required maxlength="128" pattern="[A-Za-z0-9]+" placeholder="ID резюме" autofocus />
      <div class="actions"><button :disabled="busy">Подключить</button><button type="button" class="secondary" @click="emit('close')">Отмена</button></div>
    </form>
  </div>
</template>
