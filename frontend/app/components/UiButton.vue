<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  loading?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <button 
    :class="['btn', `btn--${variant || 'primary'}`]" 
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="loader"></span>
    <span v-else class="content"><slot /></span>
  </button>
</template>

<style scoped>
.btn {
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-base);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 3rem;
  width: 100%;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn--primary {
  background: linear-gradient(135deg, var(--color-primary), #818cf8);
  color: var(--color-on-primary);
  box-shadow: var(--shadow-primary);
}

.btn--primary:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-primary-hover), var(--color-primary));
  transform: translateY(-2px);
}

.btn--secondary {
  background: var(--color-surface-variant);
  color: var(--color-on-surface);
  border: 1px solid var(--color-border);
}

.btn--secondary:hover:not(:disabled) {
  background: var(--color-surface);
}

.btn--ghost {
  background: transparent;
  color: var(--color-on-surface-variant);
}

.btn--ghost:hover:not(:disabled) {
  background: var(--color-surface-variant);
  color: var(--color-on-surface);
}

.btn--danger {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.btn--danger:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.2);
}

.loader {
  width: 20px;
  height: 20px;
  border: 2px solid currentColor;
  border-bottom-color: transparent;
  border-radius: 50%;
  animation: rotation 1s linear infinite;
}

@keyframes rotation {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
