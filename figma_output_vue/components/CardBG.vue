<template>
  <div>
  <template v-if="variant === 'Default'">
    <div class="cardbg-card-bg-1">
      <div class="cardbg-unnamed-2"></div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.cardbg-card-bg-1 {
  box-sizing: border-box;
  width: 288px;
  height: 148px;
}

.cardbg-unnamed-2 {
  box-sizing: border-box;
  width: 60px;
  height: 60px;
}
</style>
