<template>
  <div>
  <template v-if="variant === 'cartoon-M'">
    <div class="userimage-user-image-cartoon-m-1"></div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.userimage-user-image-cartoon-m-1 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  opacity: 0.0;
  border-radius: 100px 100px 100px 100px;
}
</style>
