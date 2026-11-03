<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  player: { type: Object, required: true },
  size: { type: Number, default: 44 },
  showStatus: { type: Boolean, default: false },
})
const brokenAvatar = ref(false)
const brokenFrame = ref(false)
watch(() => props.player.avatar, () => { brokenAvatar.value = false })
watch(() => props.player.frame, () => { brokenFrame.value = false })
const initials = computed(() => Array.from(props.player.name || '?').slice(0, 1).join('').toUpperCase())
const hue = computed(() => Array.from(props.player.id || props.player.name || '').reduce((n, c) => n + c.codePointAt(0), 0) * 47 % 360)
</script>

<template>
  <span class="player-avatar" :style="{ '--avatar-size': `${size}px`, '--avatar-hue': hue }">
    <span class="avatar-face">
      <img v-if="player.avatar && !brokenAvatar" :src="player.avatar" alt="" loading="lazy" @error="brokenAvatar = true" />
      <span v-else>{{ initials }}</span>
    </span>
    <img v-if="player.frame && !brokenFrame" class="avatar-decoration" :src="player.frame" alt="头像框" loading="lazy" @error="brokenFrame = true" />
    <span v-if="showStatus" class="avatar-presence" :class="{ online: player.online === true, unknown: player.online === null }" :aria-label="player.onlineLabel || '状态未知'"></span>
  </span>
</template>
