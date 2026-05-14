<script setup lang="ts">
const { state, start, reset } = useConversion()
const url = ref('')
const selectedFormat = ref('MP3')
const showDetails = ref(false)

const handleConvert = () => {
  if (!url.value) return
  start(url.value, selectedFormat.value)
}

const formatDuration = (secs: number) => {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = Math.floor(secs % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

const pasteFromClipboard = async () => {
  try {
    const text = await navigator.clipboard.readText()
    url.value = text
  } catch (err) {
    console.error('Falha ao ler área de transferência', err)
  }
}
</script>

<template>
  <div class="app-container">
    <header class="hero">
      <div class="logo">
        <span class="icon">⚡</span>
        <h1>YT<span>Convert</span></h1>
      </div>
      <p class="subtitle">Premium YouTube to MP3 & MP4 Converter</p>
    </header>

    <main class="content">
      <!-- Input Section -->
      <UiCard class="main-card">
        <div class="format-tabs">
          <button 
            @click="selectedFormat = 'MP3'" 
            :class="['tab', { active: selectedFormat === 'MP3' }]"
          >
            🎵 MP3 (Audio)
          </button>
          <button 
            @click="selectedFormat = 'MP4'" 
            :class="['tab', { active: selectedFormat === 'MP4' }]"
          >
            🎬 MP4 (Video)
          </button>
        </div>

        <div class="input-group">
          <UiInput 
            v-model="url" 
            placeholder="Cole o link do YouTube aqui..." 
            :disabled="state.isConverting"
            :error="!!state.error"
            @submit="handleConvert"
          />
          <button class="paste-btn" @click="pasteFromClipboard" title="Colar link">
            📋
          </button>
        </div>

        <UiButton 
          @click="handleConvert" 
          :loading="state.isConverting" 
          :disabled="!url"
          class="convert-btn"
        >
          {{ state.isConverting ? 'Convertendo...' : 'Iniciar Conversão' }}
        </UiButton>
      </UiCard>

      <!-- Progress Section -->
      <Transition name="fade">
        <UiCard v-if="state.isConverting || state.progress.percent > 0" class="progress-card">
          <div v-if="state.videoMetadata" class="video-preview">
            <img :src="state.videoMetadata.thumbnail" alt="Thumbnail" class="thumb" />
            <div class="meta">
              <h3>{{ state.videoMetadata.title }}</h3>
              <p>{{ state.videoMetadata.channel }} • {{ formatDuration(state.videoMetadata.duration) }}</p>
            </div>
          </div>

          <ProgressBar 
            :percent="state.progress.percent" 
            :status="state.currentStep"
            :details="state.progress.percent > 0 ? `${state.progress.size} • ${state.progress.speed} • ETA ${state.progress.eta}` : ''"
          />

          <div class="steps-log" v-if="showDetails">
            <div v-for="(step, i) in state.steps" :key="i" class="step">
              {{ step }}
            </div>
          </div>
          
          <button @click="showDetails = !showDetails" class="toggle-details">
            {{ showDetails ? 'Ocultar detalhes' : 'Ver detalhes log' }}
          </button>
        </UiCard>
      </Transition>

      <!-- Result Section -->
      <Transition name="slide">
        <UiCard v-if="state.result" class="result-card">
          <div class="success-icon">✨</div>
          <h2>Conversão Concluída!</h2>
          
          <div class="result-info">
            <div class="info-item">
              <span class="label">Arquivo</span>
              <span class="value">{{ state.result.filename }}</span>
            </div>
            <div class="info-group">
              <div class="info-item">
                <span class="label">Tamanho</span>
                <span class="value">{{ state.result.filesize_mb }} MB</span>
              </div>
              <div class="info-item">
                <span class="label">Qualidade</span>
                <span class="value">{{ state.result.quality }}</span>
              </div>
            </div>
          </div>

          <div class="actions">
            <a :href="state.result.download_url" class="download-link" :download="state.result.filename">
              <UiButton variant="primary">⬇️ Baixar Arquivo</UiButton>
            </a>
            <UiButton variant="ghost" @click="reset">Converter outro</UiButton>
          </div>
        </UiCard>
      </Transition>

      <!-- Error Section -->
      <Transition name="fade">
        <UiCard v-if="state.error" class="error-card">
          <div class="error-icon">⚠️</div>
          <h3>{{ state.error.title }}</h3>
          <p>{{ state.error.message }}</p>
          <UiButton variant="danger" @click="reset">Tentar Novamente</UiButton>
        </UiCard>
      </Transition>
    </main>

    <footer class="footer">
      <p>Desenvolvido com ❤️ pela Antigravity</p>
    </footer>
  </div>
</template>

<style>
/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.5s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active { transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-enter-from { transform: translateY(30px); opacity: 0; }

.app-container {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  min-height: 100vh;
}

.hero {
  text-align: center;
  margin-bottom: var(--space-4);
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.logo .icon {
  font-size: var(--text-4xl);
  filter: drop-shadow(0 0 10px var(--color-primary));
}

.logo h1 {
  font-size: var(--text-4xl);
  font-weight: 800;
  letter-spacing: -1px;
}

.logo h1 span {
  color: var(--color-primary);
}

.subtitle {
  color: var(--color-on-surface-variant);
  font-size: var(--text-lg);
  font-weight: 300;
}

.content {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.main-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.format-tabs {
  display: flex;
  background: var(--color-surface-variant);
  padding: var(--space-1);
  border-radius: var(--radius-md);
  gap: var(--space-1);
}

.tab {
  flex: 1;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-on-surface-variant);
  background: transparent;
}

.tab.active {
  background: var(--color-bg);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.input-group {
  display: flex;
  gap: var(--space-2);
}

.paste-btn {
  background: var(--color-surface-variant);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0 var(--space-4);
  font-size: var(--text-xl);
}

.paste-btn:hover {
  background: var(--color-surface);
}

.progress-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.video-preview {
  display: flex;
  gap: var(--space-4);
  align-items: center;
}

.video-preview .thumb {
  width: 120px;
  height: 68px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

.video-preview .meta h3 {
  font-size: var(--text-base);
  margin-bottom: var(--space-1);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.video-preview .meta p {
  font-size: var(--text-xs);
  color: var(--color-on-surface-variant);
}

.steps-log {
  background: rgba(0, 0, 0, 0.2);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  max-height: 150px;
  overflow-y: auto;
  color: var(--color-on-surface-variant);
}

.step {
  margin-bottom: 2px;
}

.toggle-details {
  background: transparent;
  color: var(--color-primary);
  font-size: var(--text-xs);
  font-weight: 600;
  text-decoration: underline;
  align-self: center;
}

.result-card {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  border: 1px solid var(--color-success);
}

.success-icon {
  font-size: var(--text-4xl);
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--color-surface-variant);
  padding: var(--space-4);
  border-radius: var(--radius-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-4);
}

.info-item .label {
  font-size: var(--text-xs);
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-item .value {
  font-weight: 600;
  word-break: break-all;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.download-link {
  text-decoration: none;
}

.error-card {
  text-align: center;
  border: 1px solid var(--color-error);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.error-icon {
  font-size: var(--text-4xl);
}

.footer {
  text-align: center;
  margin-top: auto;
  color: var(--color-on-surface-variant);
  font-size: var(--text-sm);
  padding: var(--space-8) 0;
}

@media (max-width: 600px) {
  .logo h1 { font-size: var(--text-2xl); }
  .video-preview { flex-direction: column; align-items: flex-start; }
  .video-preview .thumb { width: 100%; height: auto; aspect-ratio: 16/9; }
}
</style>
