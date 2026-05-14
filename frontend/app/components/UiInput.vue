<script setup lang="ts">
defineProps<{
  modelValue: string
  placeholder?: string
  error?: boolean
  disabled?: boolean
}>()

defineEmits(['update:modelValue', 'submit'])
</script>

<template>
  <div :class="['input-container', { 'has-error': error, 'is-disabled': disabled }]">
    <input 
      :value="modelValue"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @keydown.enter="$emit('submit')"
      :placeholder="placeholder"
      :disabled="disabled"
      class="input-field"
    />
    <div class="focus-border"></div>
  </div>
</template>

<style scoped>
.input-container {
  position: relative;
  width: 100%;
}

.input-field {
  width: 100%;
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface-variant);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-on-surface);
  font-size: var(--text-base);
  transition: var(--transition-base);
}

.input-field:focus {
  background: var(--color-surface);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
}

.input-field::placeholder {
  color: var(--color-on-surface-variant);
  opacity: 0.5;
}

.has-error .input-field {
  border-color: var(--color-error);
  animation: shake 0.5s ease-in-out;
}

.is-disabled .input-field {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-5px); }
  40%, 80% { transform: translateX(5px); }
}
</style>
