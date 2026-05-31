import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useEpochStore = defineStore('epoch', () => {
  const current = ref('30er')

  const epochClass = computed(() => `epoch-${current.value}`)

  function setEpoch(epoch) {
    if (epoch === '30er' || epoch === '90er') {
      current.value = epoch
    }
  }

  return { current, epochClass, setEpoch }
})
