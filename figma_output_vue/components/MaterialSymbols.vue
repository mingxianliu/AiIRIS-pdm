<template>
  <div>
  <template v-if="variant === 'Device&Hardware'">
    <div class="materialsymbols-materialsymbols-device-hardware-battery-horiz-075-1">
      <div class="materialsymbols-vector-2"></div>
    </div>
  </template>
  <template v-if="variant === 'UI-Action'">
    <div class="materialsymbols-materialsymbols-ui-action-error-3">
      <div class="materialsymbols-vector-4"></div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.materialsymbols-materialsymbols-device-hardware-battery-horiz-075-1 {
  box-sizing: border-box;
  width: 22px;
  height: 22px;
}

.materialsymbols-vector-2 {
  box-sizing: border-box;
  width: 17px;
  height: 8px;
  background-color: rgba(241, 245, 249, 1.0);
}

.materialsymbols-materialsymbols-ui-action-error-3 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.materialsymbols-vector-4 {
  box-sizing: border-box;
  width: 20px;
  height: 20px;
  background-color: rgba(251, 44, 54, 1.0);
}
</style>
