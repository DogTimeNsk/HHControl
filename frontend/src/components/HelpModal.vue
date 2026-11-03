<script setup lang="ts">
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="modal card help" role="dialog" aria-modal="true" aria-labelledby="help-title">
      <div class="section-heading"><h2 id="help-title">О HH Control</h2><button class="icon-button secondary" aria-label="Закрыть справку" @click="emit('close')">×</button></div>
      <p>HH Control помогает отслеживать доступность и автоматически поднимать ваши собственные резюме в поиске HeadHunter.</p>
      <p>Сначала войдите в hh.ru через VNC и сохраните сессию. Затем добавьте и синхронизируйте резюме, включите автообновление для нужных из них.</p>
      <p>«Открыть VNC» показывает текущий экран браузера без создания новой сессии. Никому не передавайте доступ к этой странице.</p>
      <div class="actions"><button @click="emit('close')">Понятно</button></div>
    </section>
  </div>
</template>
