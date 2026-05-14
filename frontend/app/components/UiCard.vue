<template>
  <div class="glass-panel card">
    <slot />
  </div>
</template>

<style scoped>
.card {
  padding: var(--space-6);
  box-shadow: var(--shadow-lg);
  transition: var(--transition-base);
}
</style>
