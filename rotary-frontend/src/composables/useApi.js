import { ref } from 'vue'
import personsJson from '@/mocks/persons.json'
import documentsJson from '@/mocks/documents.json'
import featuredJson from '@/mocks/featured.json'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_BASE = '/api/v1'

const toStub = (data) => ({ stub: true, ...data })

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  async function getPersons(params = {}) {
    loading.value = true
    try {
      if (USE_MOCK) {
        let data = [...personsJson]
        if (params.epoch) data = data.filter(p => p.epoch === params.epoch)
        if (params.q) data = data.filter(p => p.display_name.toLowerCase().includes(params.q.toLowerCase()))
        return data
      }
      const query = new URLSearchParams(params).toString()
      const res = await fetch(`${API_BASE}/persons?${query}`)
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getPerson(slug) {
    loading.value = true
    try {
      if (USE_MOCK) {
        const person = personsJson.find(p => p.slug === slug)
        if (!person) throw new Error('Person not found')
        if (!person.is_public && !isAuthenticated()) return toStub(person)
        return person
      }
      const res = await fetch(`${API_BASE}/persons/${slug}`)
      if (res.status === 404) throw new Error('Person not found')
      const data = await res.json()
      if (data.stub) return data
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getDocuments(params = {}) {
    loading.value = true
    try {
      if (USE_MOCK) {
        let data = [...documentsJson]
        if (params.epoch) data = data.filter(d => d.epoch === params.epoch)
        return data
      }
      const query = new URLSearchParams(params).toString()
      const res = await fetch(`${API_BASE}/documents?${query}`)
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getDocument(id) {
    loading.value = true
    try {
      if (USE_MOCK) {
        const doc = documentsJson.find(d => d.id === parseInt(id))
        if (!doc) throw new Error('Document not found')
        return doc
      }
      const res = await fetch(`${API_BASE}/documents/${id}`)
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function getFeatured() {
    if (USE_MOCK) return featuredJson
    const res = await fetch(`${API_BASE}/featured`)
    return await res.json()
  }

  function isAuthenticated() {
    return !!localStorage.getItem('access_token')
  }

  return {
    loading,
    error,
    getPersons,
    getPerson,
    getDocuments,
    getDocument,
    getFeatured
  }
}
