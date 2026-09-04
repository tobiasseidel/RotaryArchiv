import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAdminStore = defineStore('admin', () => {
  const documents = ref([])
  const jobs = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function uploadDocument(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch('/api/documents/', {
      method: 'POST',
      credentials: 'include',
      body: formData
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Fehler beim Hochladen')
    }

    return await response.json()
  }

  async function fetchDocuments(params = {}) {
    loading.value = true
    error.value = null

    try {
      const query = new URLSearchParams()
      if (params.skip) query.set('skip', params.skip)
      if (params.limit) query.set('limit', params.limit)
      if (params.status_filter) query.set('status_filter', params.status_filter)

      const response = await fetch(`/api/documents/summary?${query}`, {
        credentials: 'include'
      })

      if (!response.ok) throw new Error('Fehler beim Laden der Dokumente')
      documents.value = await response.json()
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchJobs(params = {}) {
    loading.value = true
    error.value = null

    try {
      const query = new URLSearchParams()
      if (params.status) query.set('status', params.status)
      if (params.job_type) query.set('job_type', params.job_type)
      if (params.limit) query.set('limit', params.limit)

      const response = await fetch(`/api/ocr/jobs?${query}`, {
        credentials: 'include'
      })

      if (!response.ok) throw new Error('Fehler beim Laden der Jobs')
      jobs.value = await response.json()
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function batchUpdateJobs(jobIds, action) {
    const response = await fetch('/api/ocr/jobs/batch', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_ids: jobIds, action })
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Fehler bei der Aktion')
    }

    return await response.json()
  }

  async function prioritizeJob(jobId) {
    const response = await fetch(`/api/ocr/jobs/${jobId}/prioritize`, {
      method: 'POST',
      credentials: 'include'
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Fehler beim Priorisieren')
    }

    return await response.json()
  }

  const pendingJobs = computed(() =>
    jobs.value.filter(j => j.status === 'PENDING')
  )

  const runningJobs = computed(() =>
    jobs.value.filter(j => j.status === 'RUNNING')
  )

  const completedJobs = computed(() =>
    jobs.value.filter(j => j.status === 'COMPLETED')
  )

  const failedJobs = computed(() =>
    jobs.value.filter(j => j.status === 'FAILED')
  )

  return {
    documents,
    jobs,
    loading,
    error,
    uploadDocument,
    fetchDocuments,
    fetchJobs,
    batchUpdateJobs,
    prioritizeJob,
    pendingJobs,
    runningJobs,
    completedJobs,
    failedJobs
  }
})
