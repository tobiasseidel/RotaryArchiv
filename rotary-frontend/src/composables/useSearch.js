import { ref } from 'vue'
import personsJson from '@/mocks/persons.json'
import documentsJson from '@/mocks/documents.json'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_BASE = '/api/v1'

export function useSearch() {
  const loading = ref(false)
  const error = ref(null)

  function searchLocal(term, epoch) {
    const q = term.toLowerCase().trim()
    const results = []

    for (const p of personsJson) {
      if (!p.is_public) continue
      if (epoch && p.epoch !== epoch) continue
      if (p.display_name.toLowerCase().includes(q) || (p.notes || '').toLowerCase().includes(q)) {
        results.push({
          type: 'person',
          id: p.id,
          slug: p.slug,
          display_name: p.display_name,
          epoch: p.epoch,
          snippet: p.notes,
          portrait_url: p.portrait_url,
        })
      }
    }

    for (const d of documentsJson) {
      if (epoch && d.epoch !== epoch) continue
      const match = (d.title || '').toLowerCase().includes(q)
        || (d.context_snippet || '').toLowerCase().includes(q)
        || (d.transcription || '').toLowerCase().includes(q)
      if (match) {
        results.push({
          type: 'document',
          id: d.id,
          slug: String(d.id),
          display_name: d.title || `Dokument #${d.id}`,
          epoch: d.epoch,
          snippet: d.context_snippet || d.transcription?.slice(0, 120),
          document_id: d.id,
        })
      }
    }

    return results
  }

  async function search(term, epoch) {
    loading.value = true
    error.value = null
    try {
      if (USE_MOCK) {
        return searchLocal(term, epoch)
      }
      const params = { q: term }
      if (epoch) params.epoch = epoch
      const query = new URLSearchParams(params).toString()
      const res = await fetch(`${API_BASE}/search?${query}`)
      if (!res.ok) throw new Error('Suche fehlgeschlagen')
      return await res.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { loading, error, search }
}
