<script setup>
import { ref, computed } from 'vue'
import { useAdminStore } from '@/stores/admin'
import AdminLayout from '@/components/AdminLayout.vue'

const adminStore = useAdminStore()

const isDragging = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref(null) // null | 'uploading' | 'success' | 'error'
const uploadError = ref(null)
const selectedFiles = ref([])

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  addFiles(files)
}

function onFileSelect(e) {
  const files = Array.from(e.target.files)
  addFiles(files)
  e.target.value = ''
}

function addFiles(files) {
  const pdfFiles = files.filter(f => f.type === 'application/pdf')
  selectedFiles.value.push(...pdfFiles)
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

async function uploadFiles() {
  if (selectedFiles.value.length === 0) return

  uploadStatus.value = 'uploading'
  uploadProgress.value = 0
  uploadError.value = null

  try {
    const total = selectedFiles.value.length
    let uploaded = 0

    for (const file of selectedFiles.value) {
      await adminStore.uploadDocument(file)
      uploaded++
      uploadProgress.value = Math.round((uploaded / total) * 100)
    }

    uploadStatus.value = 'success'
    selectedFiles.value = []
    setTimeout(() => {
      uploadStatus.value = null
    }, 3000)
  } catch (err) {
    uploadStatus.value = 'error'
    uploadError.value = err.message || 'Fehler beim Hochladen'
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <AdminLayout>
    <div class="upload-page">
      <h1 class="page-title">PDF-Upload</h1>

      <div
        class="dropzone"
        :class="{ dragging: isDragging, 'has-files': selectedFiles.length > 0 }"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
        <input
          type="file"
          id="file-input"
          accept=".pdf"
          multiple
          class="file-input"
          @change="onFileSelect"
        />
        <label for="file-input" class="dropzone-content">
          <div class="dropzone-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <polyline points="9 15 12 12 15 15"/>
            </svg>
          </div>
          <div class="dropzone-text">
            <span v-if="!isDragging">PDF-Dateien hierher ziehen oder klicken zum Auswählen</span>
            <span v-else>Dateien loslassen zum Hochladen</span>
          </div>
          <div class="dropzone-hint">Unterstützt PDF-Dateien</div>
        </label>
      </div>

      <div v-if="selectedFiles.length > 0" class="file-list">
        <div class="file-list-header">
          <h2 class="file-list-title">Ausgewählte Dateien ({{ selectedFiles.length }})</h2>
          <button @click="selectedFiles = []" class="clear-btn">Alle entfernen</button>
        </div>

        <div class="file-items">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
            <div class="file-info">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
            </div>
            <button @click="removeFile(index)" class="remove-btn" title="Entfernen">×</button>
          </div>
        </div>

        <div class="upload-actions">
          <button
            @click="uploadFiles"
            class="upload-btn"
            :disabled="uploadStatus === 'uploading'"
          >
            <span v-if="uploadStatus === 'uploading'">
              Hochladen... {{ uploadProgress }}%
            </span>
            <span v-else>
              {{ selectedFiles.length }} {{ selectedFiles.length === 1 ? 'Datei' : 'Dateien' }} hochladen
            </span>
          </button>
        </div>
      </div>

      <div v-if="uploadStatus === 'success'" class="upload-message success">
        Dateien erfolgreich hochgeladen!
      </div>

      <div v-if="uploadStatus === 'error'" class="upload-message error">
        {{ uploadError }}
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.upload-page {
  max-width: 800px;
}

.page-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  color: var(--color-text-primary);
  margin-bottom: var(--space-l);
}

.dropzone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  transition: all var(--transition-fast);
  cursor: pointer;
}

.dropzone:hover,
.dropzone.dragging {
  border-color: var(--color-epoch-primary);
  background: var(--color-bg);
}

.file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  overflow: hidden;
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-2xl) var(--space-l);
  cursor: pointer;
}

.dropzone-icon {
  color: var(--color-stub);
  margin-bottom: var(--space-m);
}

.dropzone-text {
  font-family: var(--font-sans);
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.dropzone-hint {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-stub);
}

.file-list {
  margin-top: var(--space-l);
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-m);
}

.file-list-title {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.clear-btn {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-stub);
  background: none;
  border: none;
  cursor: pointer;
}

.clear-btn:hover {
  color: var(--color-error);
}

.file-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-s) var(--space-m);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--space-m);
}

.file-name {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.file-size {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-stub);
}

.remove-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--color-stub);
  cursor: pointer;
  padding: 0 var(--space-xs);
  line-height: 1;
}

.remove-btn:hover {
  color: var(--color-error);
}

.upload-actions {
  margin-top: var(--space-m);
}

.upload-btn {
  padding: var(--space-s) var(--space-l);
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
  background: var(--color-epoch-primary);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.upload-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-message {
  margin-top: var(--space-m);
  padding: var(--space-s) var(--space-m);
  border-radius: 4px;
  font-family: var(--font-sans);
  font-size: 0.875rem;
}

.upload-message.success {
  background: #DCFCE7;
  color: #166534;
  border: 1px solid #BBF7D0;
}

.upload-message.error {
  background: #FEE2E2;
  color: #991B1B;
  border: 1px solid #FECACA;
}
</style>
