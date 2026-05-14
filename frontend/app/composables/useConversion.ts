import { ref } from 'vue'

export interface ConversionState {
  isConverting: boolean
  currentStep: string
  steps: string[]
  progress: {
    percent: number
    size: string
    speed: string
    eta: string
  }
  videoMetadata: {
    title: string
    thumbnail: string
    channel: string
    duration: number
  } | null
  result: {
    filename: string
    download_url: string
    filesize_mb: number
    quality: string
    duration: number
  } | null
  error: {
    title: string
    message: string
  } | null
}

export const useConversion = () => {
  const state = ref<ConversionState>({
    isConverting: false,
    currentStep: '',
    steps: [],
    progress: { percent: 0, size: '', speed: '', eta: '' },
    videoMetadata: null,
    result: null,
    error: null
  })

  let eventSource: EventSource | null = null

  const reset = () => {
    state.value = {
      isConverting: false,
      currentStep: '',
      steps: [],
      progress: { percent: 0, size: '', speed: '', eta: '' },
      videoMetadata: null,
      result: null,
      error: null
    }
  }

  const start = async (url: string, format: string) => {
    reset()
    state.value.isConverting = true
    state.value.currentStep = 'Validando o link...'
    state.value.steps.push(state.value.currentStep)

    try {
      const response = await fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, format })
      })

      const data = await response.json()

      if (!response.ok || data.error) {
        throw new Error(data.error || 'Falha ao iniciar conversão')
      }

      connectSSE(data.session_id)
    } catch (err: any) {
      state.value.isConverting = false
      state.value.error = {
        title: 'Erro ao iniciar',
        message: err.message
      }
    }
  }

  const connectSSE = (sessionId: string) => {
    if (eventSource) eventSource.close()

    eventSource = new EventSource(`/api/events/${sessionId}`)

    eventSource.onmessage = (e) => {
      const ev = JSON.parse(e.data)
      handleEvent(ev)
    }

    eventSource.onerror = () => {
      if (eventSource) eventSource.close()
      if (!state.value.result && !state.value.error) {
        state.value.error = {
          title: 'Conexão perdida',
          message: 'A conexão com o servidor foi interrompida.'
        }
      }
      state.value.isConverting = false
    }
  }

  const handleEvent = (ev: any) => {
    switch (ev.type) {
      case 'status':
        state.value.currentStep = ev.message
        state.value.steps.push(ev.message)
        break
      case 'metadata':
        state.value.videoMetadata = {
          title: ev.title,
          thumbnail: ev.thumbnail,
          channel: ev.channel,
          duration: ev.duration
        }
        state.value.steps.push(`✅ Vídeo encontrado: ${ev.title}`)
        break
      case 'progress':
        state.value.progress = {
          percent: Math.min(Math.max(ev.percent, 0), 99),
          size: ev.size,
          speed: ev.speed,
          eta: ev.eta
        }
        break
      case 'retry':
        state.value.currentStep = `🔄 ${ev.message}`
        state.value.steps.push(state.value.currentStep)
        break
      case 'success':
        state.value.progress.percent = 100
        state.value.result = ev
        state.value.isConverting = false
        if (eventSource) {
          eventSource.close()
          eventSource = null
        }
        break
      case 'error':
        state.value.error = {
          title: 'Não foi possível converter',
          message: ev.message
        }
        state.value.isConverting = false
        if (eventSource) {
          eventSource.close()
          eventSource = null
        }
        break
    }
  }

  return {
    state,
    start,
    reset
  }
}
