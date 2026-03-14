<template>
  <div>
  <template v-if="variant === 'Default'">
    <div class="iconactive-icon-active-1">
      <div class="iconactive-vector-2"></div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.iconactive-icon-active-1 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  opacity: 0.0;
}

.iconactive-vector-2 {
  box-sizing: border-box;
  width: 19px;
  height: 21px;
  background-color: rgba(255, 255, 255, 0.699999988079071);
}
</style>
