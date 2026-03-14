<template>
  <div>
  <template v-if="variant === 'Default'">
    <div class="tag-tag-1">
      <div class="tag-tag-2">
        <span class="tag-tag-3">水平滾動

從使用者最初
使用月份到現在
（最多三年）

無使用的
月份即0點</span>
      </div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.tag-tag-1 {
  box-sizing: border-box;
  width: 40px;
  height: 40px;
}

.tag-tag-2 {
  box-sizing: border-box;
  width: 128px;
  height: 176px;
  background-color: rgba(190, 206, 227, 1.0);
  display: flex;
  flex-direction: row;
  gap: 4px;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  justify-content: center;
  align-items: center;
}

.tag-tag-3 {
  box-sizing: border-box;
  width: 112px;
  height: 160px;
  background-color: rgba(29, 41, 61, 1.0);
  font-size: 16px;
  font-family: Noto Sans TC;
  font-weight: 500;
  line-height: 20px;
  letter-spacing: 0.0px;
  text-align: center;
  color: rgb(29, 41, 61);
}
</style>
