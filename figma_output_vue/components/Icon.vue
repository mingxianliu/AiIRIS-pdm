<template>
  <div>
  <template v-if="variant === 'Default'">
    <div class="icon-icon-1">
      <div class="icon-vector-2"></div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.icon-icon-1 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.icon-vector-2 {
  box-sizing: border-box;
  width: 15px;
  height: 15px;
  background-color: rgba(255, 255, 255, 0.800000011920929);
}
</style>
