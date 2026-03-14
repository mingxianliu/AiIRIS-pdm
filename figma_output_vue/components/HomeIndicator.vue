<template>
  <div>
  <template v-if="variant === 'Default'">
    <div class="homeindicator-home-indicator-1">
      <div class="homeindicator-home-indicator-2"></div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.homeindicator-home-indicator-1 {
  box-sizing: border-box;
  width: 360px;
  height: 34px;
}

.homeindicator-home-indicator-2 {
  box-sizing: border-box;
  width: 144px;
  height: 5px;
  background-color: rgba(0, 0, 0, 1.0);
  border-radius: 100px 100px 100px 100px;
}
</style>
