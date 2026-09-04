<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAdminStore } from '@/stores/admin'
import AdminLayout from '@/components/AdminLayout.vue'

const adminStore = useAdminStore()

const statusFilter = ref(null)
const selectedJobs = ref([])
const isRefreshing = ref(false)

const statusOptions = [
  { value: null, label: 'Alle' },
  { value: 'PENDING', label: 'Ausstehend' },
  { value: 'RUNNING', label: 'Laufend' },
  { value: 'COMPLETED', label: 'Fertig' },
  { value: 'FAILED', label: 'Fehlgeschlagen' },
  { value: 'CANCELLED', label: 'Abgebrochen' }
]

onMounted(async () => {
  await loadJobs()
})

async function loadJobs() {
  await adminStore.fetchJobs({
    status: statusFilter.value,
    limit: 100
  })
}

async function handleRefresh() {
  isRefreshing.value = true
  await loadJobs()
  setTimeout(() => { isRefreshing.value = false }, 500)
}

function toggleJobSelection(jobId) {
  const index = selectedJobs.value.indexOf(jobId)
  if (index === -1) {
    selectedJobs.value.push(jobId)
  } else {
    selectedJobs.value.splice(index, 1)
  }
}

function toggleSelectAll() {
  if (selectedJobs.value.length === adminStore.jobs.length) {
    selectedJobs.value = []
  } else {
    selectedJobs.value = adminStore.jobs.map(j => j.id)
  }
}

async function handleBatchCancel() {
  if (selectedJobs.value.length === 0) return
  try {
    await adminStore.batchUpdateJobs(selectedJobs.value, 'cancel')
    selectedJobs.value = []
    await loadJobs()
  } catch (err) {
    console.error('Batch cancel failed:', err)
  }
}

async function handleBatchRestart() {
  if (selectedJobs.value.length === 0) return
  try {
    await adminStore.batchUpdateJobs(selectedJobs.value, 'restart')
    selectedJobs.value = []
    await loadJobs()
  } catch (err) {
    console.error('Batch restart failed:', err)
  }
}

async function handlePrioritize(jobId) {
  try {
    await adminStore.prioritizeJob(jobId)
    await loadJobs()
  } catch (err) {
    console.error('Prioritize failed:', err)
  }
}

function getStatusClass(status) {
  const classes = {
    PENDING: 'status-pending',
    RUNNING: 'status-running',
    COMPLETED: 'status-completed',
    FAILED: 'status-failed',
    CANCELLED: 'status-cancelled'
  }
  return classes[status] || ''
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <AdminLayout>
    <div class="queue-page">
      <div class="page-header">
        <h1 class="page-title">Job-Queue</h1>
        <button @click="handleRefresh" class="refresh-btn" :disabled="isRefreshing">
          <span :class="{ spinning: isRefreshing }">↻</span> Aktualisieren
        </button>
      </div>

      <div class="filters">
        <select v-model="statusFilter" @change="loadJobs" class="status-filter">
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>

        <div v-if="selectedJobs.length > 0" class="batch-actions">
          <span class="selection-count">{{ selectedJobs.length }} ausgewählt</span>
          <button @click="handleBatchCancel" class="batch-btn">Abbrechen</button>
          <button @click="handleBatchRestart" class="batch-btn">Neustart</button>
        </div>
      </div>

      <div v-if="adminStore.loading && adminStore.jobs.length === 0" class="loading">
        Lade Jobs...
      </div>

      <div v-else-if="adminStore.jobs.length === 0" class="empty-state">
        Keine Jobs gefunden
      </div>

      <div v-else class="job-table-wrapper">
        <table class="job-table">
          <thead>
            <tr>
              <th class="col-check">
                <input
                  type="checkbox"
                  :checked="selectedJobs.length === adminStore.jobs.length"
                  @change="toggleSelectAll"
                />
              </th>
              <th class="col-id">ID</th>
              <th class="col-document">Dokument</th>
              <th class="col-type">Typ</th>
              <th class="col-page">Seite</th>
              <th class="col-status">Status</th>
              <th class="col-priority">Prio</th>
              <th class="col-created">Erstellt</th>
              <th class="col-actions">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in adminStore.jobs" :key="job.id">
              <td class="col-check">
                <input
                  type="checkbox"
                  :checked="selectedJobs.includes(job.id)"
                  @change="toggleJobSelection(job.id)"
                />
              </td>
              <td class="col-id">{{ job.id }}</td>
              <td class="col-document">{{ job.document_id }}</td>
              <td class="col-type">{{ job.job_type }}</td>
              <td class="col-page">{{ job.page_number || '-' }}</td>
              <td class="col-status">
                <span :class="['status-badge', getStatusClass(job.status)]">
                  {{ job.status }}
                </span>
              </td>
              <td class="col-priority">{{ job.priority || '-' }}</td>
              <td class="col-created">{{ formatDate(job.created_at) }}</td>
              <td class="col-actions">
                <button
                  v-if="job.status === 'PENDING'"
                  @click="handlePrioritize(job.id)"
                  class="action-btn"
                  title="Priorisieren"
                >
                  ↑
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.queue-page {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-l);
}

.page-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  color: var(--color-text-primary);
  margin: 0;
}

.refresh-btn {
  padding: var(--space-s) var(--space-m);
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.refresh-btn:hover:not(:disabled) {
  background: var(--color-bg);
  border-color: var(--color-text-secondary);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.filters {
  display: flex;
  align-items: center;
  gap: var(--space-m);
  margin-bottom: var(--space-l);
}

.status-filter {
  padding: var(--space-s) var(--space-m);
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: var(--space-s);
}

.selection-count {
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-stub);
}

.batch-btn {
  padding: var(--space-xs) var(--space-s);
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}

.batch-btn:hover {
  background: var(--color-bg);
  border-color: var(--color-text-secondary);
}

.loading,
.empty-state {
  padding: var(--space-2xl);
  text-align: center;
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-stub);
}

.job-table-wrapper {
  overflow-x: auto;
}

.job-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-sans);
  font-size: 0.8125rem;
}

.job-table th {
  text-align: left;
  padding: var(--space-s) var(--space-m);
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.job-table td {
  padding: var(--space-s) var(--space-m);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
}

.job-table tbody tr:hover {
  background: var(--color-bg);
}

.col-check {
  width: 40px;
}

.col-check input {
  cursor: pointer;
}

.col-id {
  width: 60px;
}

.col-page {
  width: 80px;
}

.col-priority {
  width: 60px;
}

.col-created {
  width: 140px;
}

.col-actions {
  width: 60px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-pending {
  background: #FEF3C7;
  color: #92400E;
}

.status-running {
  background: #DBEAFE;
  color: #1E40AF;
}

.status-completed {
  background: #D1FAE5;
  color: #065F46;
}

.status-failed {
  background: #FEE2E2;
  color: #991B1B;
}

.status-cancelled {
  background: #E5E7EB;
  color: #374151;
}

.action-btn {
  padding: 2px 6px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  cursor: pointer;
}

.action-btn:hover {
  background: var(--color-bg);
  color: var(--color-epoch-primary);
  border-color: var(--color-epoch-primary);
}
</style>
