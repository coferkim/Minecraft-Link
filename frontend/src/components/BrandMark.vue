<script setup>
defineProps({ compact: Boolean })
</script>

<template>
  <div class="brand" :class="{ 'brand-compact': compact }">
    <img src="/minecraft-link.svg" alt="" width="27" height="27" />
    <span v-if="!compact"><strong>Minecraft Link</strong><small>Minecraft 客户端接口桥接器</small></span>
  </div>
</template>
