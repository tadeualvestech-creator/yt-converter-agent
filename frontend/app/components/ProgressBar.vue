<script setup lang="ts">
defineProps<{
  percent: number
  status: string
  details?: string
}>()
</script>

<template>
  <div class="progress-wrapper">
    <div class="header">
      <span class="status">{{ status }}</span>
      <span class="percent">{{ Math.round(percent) }}%</span>
    </div>
    
    <div class="bar-container">
      <div class="bar-glow" :style="{ width: `${percent}%` }"></div>
      <div class="bar-fill" :style="{ width: `${percent}%` }"></div>
    </div>
    
    <div v-if="details" class="details">
      {{ details }}
    </div>
  </div>
</template>

<style scoped>
.progress-wrapper {
  width: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-on-surface-variant);
}

.percent {
  font-weight: 700;
  color: var(--color-primary);
}

.bar-container {
  position: relative;
  height: 10px;
  background: var(--color-surface-variant);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
  z-index: 2;
}

.bar-glow {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--color-primary);
  filter: blur(8px);
  opacity: 0.5;
  transition: width 0.3s ease;
  z-index: 1;
}

.details {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-on-surface-variant);
  text-align: center;
  font-family: var(--font-mono);
}
</style>
