<template>
  <div>
  <template v-if="variant === 'wrench-01'">
    <div class="hugeicons-hugeicons-wrench-01-1">
      <div class="hugeicons-vector-2"></div>
    </div>
  </template>
  <template v-if="variant === 'quiz-03'">
    <div class="hugeicons-hugeicons-quiz-03-3">
      <div class="hugeicons-vector-4"></div>
    </div>
  </template>
  <template v-if="variant === 'meeting-room'">
    <div class="hugeicons-hugeicons-meeting-room-5">
      <div class="hugeicons-vector-6"></div>
    </div>
  </template>
  <template v-if="variant === 'recycle-02'">
    <div class="hugeicons-hugeicons-recycle-02-7">
      <div class="hugeicons-vector-8"></div>
    </div>
  </template>
  <template v-if="variant === 'mailbox-01'">
    <div class="hugeicons-hugeicons-mailbox-01-9">
      <div class="hugeicons-vector-10"></div>
    </div>
  </template>
  <template v-if="variant === 'security-lock'">
    <div class="hugeicons-hugeicons-security-lock-11">
      <div class="hugeicons-vector-12"></div>
    </div>
  </template>
  <template v-if="variant === 'paint-brush-04'">
    <div class="hugeicons-hugeicons-paint-brush-04-13">
      <div class="hugeicons-vector-14"></div>
    </div>
  </template>
  <template v-if="variant === 'home-07'">
    <div class="hugeicons-hugeicons-home-07-15">
      <div class="hugeicons-vector-16"></div>
    </div>
  </template>
  <template v-if="variant === 'user-account'">
    <div class="hugeicons-hugeicons-user-account-17">
      <div class="hugeicons-vector-18"></div>
    </div>
  </template>
  <template v-if="variant === 'more-01'">
    <div class="hugeicons-hugeicons-more-01-19">
      <div class="hugeicons-vector-20"></div>
    </div>
  </template>
  <template v-if="variant === 'headset'">
    <div class="hugeicons-hugeicons-headset-21">
      <div class="hugeicons-vector-22"></div>
    </div>
  </template>
  </div>
</template>

<script setup>
const props = defineProps({ variant: { type: String, default: 'Default' } });
</script>

<style scoped>
.hugeicons-hugeicons-wrench-01-1 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-2 {
  box-sizing: border-box;
  width: 20px;
  height: 20px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-quiz-03-3 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-4 {
  box-sizing: border-box;
  width: 18px;
  height: 21px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-meeting-room-5 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-6 {
  box-sizing: border-box;
  width: 19px;
  height: 19px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-recycle-02-7 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-8 {
  box-sizing: border-box;
  width: 21px;
  height: 21px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-mailbox-01-9 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-10 {
  box-sizing: border-box;
  width: 20px;
  height: 21px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-security-lock-11 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-12 {
  box-sizing: border-box;
  width: 20px;
  height: 21px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-paint-brush-04-13 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
}

.hugeicons-vector-14 {
  box-sizing: border-box;
  width: 17px;
  height: 21px;
  background-color: rgba(0, 117, 149, 1.0);
}

.hugeicons-hugeicons-home-07-15 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  opacity: 0.0;
}

.hugeicons-vector-16 {
  box-sizing: border-box;
  width: 21px;
  height: 20px;
  background-color: rgba(0, 146, 184, 1.0);
}

.hugeicons-hugeicons-user-account-17 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  opacity: 0.0;
}

.hugeicons-vector-18 {
  box-sizing: border-box;
  width: 21px;
  height: 17px;
  background-color: rgba(144, 161, 185, 1.0);
}

.hugeicons-hugeicons-more-01-19 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  opacity: 0.0;
}

.hugeicons-vector-20 {
  box-sizing: border-box;
  width: 15px;
  height: 15px;
  background-color: rgba(144, 161, 185, 1.0);
}

.hugeicons-hugeicons-headset-21 {
  box-sizing: border-box;
  width: 24px;
  height: 24px;
  opacity: 0.0;
}

.hugeicons-vector-22 {
  box-sizing: border-box;
  width: 19px;
  height: 21px;
  background-color: rgba(144, 161, 185, 1.0);
}
</style>
