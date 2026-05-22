<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  bbox: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['submit', 'close'])

const suggestion = ref('')
const textareaRef = ref(null)
const previousActiveElement = ref(null)

const contextInfo = computed(() => {
  if (!props.bbox) return ''
  const y1 = Math.round(props.bbox.y1 || 0)
  const y2 = Math.round(props.bbox.y2 || 0)
  const page = props.bbox.page || 1
  return `Zeile ${y1}–${y2} auf Seite ${page}`
})

function handleSubmit() {
  if (suggestion.value.trim()) {
    emit('submit', props.bbox.id, suggestion.value.trim())
  }
}

function handleKeydown(e) {
  if (e.key === 'Escape') {
    emit('close')
  }
  if (e.key === 'Tab') {
    const focusable = textareaRef.value
    if (e.shiftKey && document.activeElement === focusable) {
      e.preventDefault()
      const closeBtn = document.getElementById('modal-close-btn')
      closeBtn?.focus()
    } else if (!e.shiftKey && document.activeElement?.id === 'modal-close-btn') {
      e.preventDefault()
      focusable?.focus()
    }
  }
}

function handleOverlayClick(e) {
  if (e.target === e.currentTarget) {
    emit('close')
  }
}

onMounted(() => {
  previousActiveElement.value = document.activeElement
  nextTick(() => {
    textareaRef.value?.focus()
  })
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  previousActiveElement.value?.focus()
})
</script>

<template>
  <div
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
    @click="handleOverlayClick"
  >
    <div class="modal-card">
      <div class="modal-header">
        <h2 id="modal-title" class="modal-title">Können Sie diese Stelle lesen?</h2>
        <button
          id="modal-close-btn"
          type="button"
          class="modal-close"
          aria-label="Schließen"
          @click="emit('close')"
        >
          &times;
        </button>
      </div>

      <p class="modal-context">{{ contextInfo }}</p>

      <p class="modal-explanation">
        Die OCR-Erkennung konnte diese Passage nicht zuverlässig lesen.
        Wenn Sie den Text erkennen, helfen Sie uns, das Archiv zu vervollständigen.
      </p>

      <form class="modal-form" @submit.prevent="handleSubmit">
        <label for="suggestion-text" class="modal-label">Ihr Vorschlag</label>
        <textarea
          id="suggestion-text"
          ref="textareaRef"
          v-model="suggestion"
          class="modal-textarea"
          rows="4"
          placeholder="Was steht Ihrer Meinung nach an dieser Stelle? ..."
          aria-required="true"
        ></textarea>

        <div class="modal-actions">
          <button
            type="button"
            class="btn-cancel"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button
            type="submit"
            class="btn-submit"
            :disabled="!suggestion.trim()"
          >
            Absenden
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: var(--space-l);
}

.modal-card {
  background: var(--color-surface);
  border-radius: 12px;
  max-width: 520px;
  width: 100%;
  padding: var(--space-xl);
  box-shadow: 0 16px 48px rgba(28, 25, 23, 0.2);
  animation: modal-in 200ms ease-out;
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-m);
}

.modal-title {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: var(--space-xs);
  line-height: 1;
  border-radius: 4px;
}

.modal-close:hover {
  color: var(--color-text-primary);
  background: var(--color-bg);
}

.modal-context {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-stub);
  background: var(--color-bg);
  padding: var(--space-s) var(--space-m);
  border-radius: 4px;
  margin-bottom: var(--space-m);
}

.modal-explanation {
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin-bottom: var(--space-l);
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-m);
}

.modal-label {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.modal-textarea {
  font-family: var(--font-serif);
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--space-m);
  resize: vertical;
  min-height: 100px;
  transition: border-color var(--transition-fast);
}

.modal-textarea:focus {
  outline: 2px solid var(--color-epoch-primary);
  outline-offset: -1px;
  border-color: transparent;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-m);
}

.btn-cancel {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  background: none;
  border: 1px solid var(--color-border);
  padding: var(--space-s) var(--space-l);
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-cancel:hover {
  background: var(--color-bg);
}

.btn-submit {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-surface);
  background: var(--color-epoch-primary);
  border: none;
  padding: var(--space-s) var(--space-l);
  border-radius: 6px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-submit:hover:not(:disabled) {
  background: var(--color-epoch-accent);
}

.btn-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
