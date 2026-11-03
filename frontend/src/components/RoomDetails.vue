<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { AlertCircle, Check, Copy, Crown, Gamepad2, LoaderCircle, RefreshCw, Users } from '@lucide/vue'
import { api, getErrorMessage, normalizeRoom } from '../api'
import { ensureUpstreamOk, roomEntity, roomMembers } from '../room-utils'
import AppDialog from './AppDialog.vue'
import PlayerAvatar from './PlayerAvatar.vue'

const props = defineProps({ room: { type: Object, default: null }, friendIds: { type: Array, default: () => [] } })
const emit = defineEmits(['close'])
const current = ref(null)
const members = ref([])
const loading = ref(false)
const error = ref('')
const raw = ref(null)
const copied = ref(false)
let request = 0
let copyTimer
const owner = computed(() => members.value.find(member => member.isOwner))
const friendCount = computed(() => members.value.filter(member => member.isFriend).length)

async function load() {
  const room = props.room
  const version = ++request
  if (!room?.id) { current.value = null; loading.value = false; return }
  current.value = room
  members.value = []
  raw.value = null
  error.value = ''
  loading.value = true
  const responses = await Promise.allSettled([api.room(room.id), api.roomMembers(room.id)])
  if (version !== request) return
  const failures = []
  responses.forEach((response, index) => {
    try {
      if (response.status === 'rejected') throw response.reason
      const payload = response.value.data
      ensureUpstreamOk(payload)
      if (index === 0) {
        const entity = roomEntity(payload)
        current.value = normalizeRoom({ ...(room.raw || room), ...(entity || {}) })
        raw.value = payload
      } else members.value = roomMembers(payload, current.value, props.friendIds)
    } catch (err) { failures.push(getErrorMessage(err, index === 0 ? '房间资料读取失败' : '房间成员读取失败')) }
  })
  error.value = failures.join('；')
  loading.value = false
}

async function copy() {
  try {
    await navigator.clipboard.writeText(current.value.id)
    copied.value = true
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 1800)
  } catch { error.value = '复制失败，请手动选择房间号' }
}
watch(() => props.room?.id, load, { immediate: true })
onUnmounted(() => { request++; clearTimeout(copyTimer) })
</script>

<template>
  <AppDialog :open="Boolean(room)" :title="current?.name || room?.name || '房间详情'" subtitle="联机房间" drawer @close="emit('close')">
    <template v-if="current">
      <div class="room-identity"><Gamepad2 :size="24" /><div><small>房间号</small><code>{{ current.id }}</code></div><button class="icon-button" type="button" title="复制房间号" aria-label="复制房间号" @click="copy"><Check v-if="copied" :size="17" /><Copy v-else :size="17" /></button></div>
      <dl class="detail-facts">
        <div><dt>房间人数</dt><dd>{{ current.memberCount ?? (loading ? '—' : members.length) }}<span v-if="current.maxMembers"> / {{ current.maxMembers }}</span></dd></div>
        <div><dt>房主</dt><dd>{{ owner?.name || current.ownerName || '—' }}</dd></div>
        <div><dt>好友</dt><dd>{{ loading ? '—' : `${friendCount} 位` }}</dd></div>
        <div><dt>地图 / 服务器</dt><dd>{{ current.mapName || current.serverName || '—' }}</dd></div>
      </dl>
      <div class="section-heading"><h3><Users :size="16" />房间成员 <span>{{ members.length }}</span></h3><button class="icon-button" type="button" :disabled="loading" title="刷新房间" aria-label="刷新房间" @click="load"><RefreshCw :size="15" :class="{ spin: loading }" /></button></div>
      <div v-if="error" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ error }}</span><button type="button" @click="load">重试</button></div>
      <div v-if="loading" class="member-skeletons" aria-label="正在读取房间成员"><div v-for="i in 5" :key="i" class="skeleton member-skeleton"></div></div>
      <div v-else-if="members.length" class="member-list">
        <div v-for="(member, index) in members" :key="member.id || index" class="member-row">
          <PlayerAvatar :player="member" :size="38" />
          <div class="member-identity"><strong>{{ member.name }}<Crown v-if="member.isOwner" :size="13" class="owner-icon" /></strong><code>{{ member.id || '—' }}</code></div>
          <div class="member-labels"><span v-if="member.isOwner" class="badge">房主</span><span v-if="member.isFriend" class="badge positive">好友</span><span v-if="member.level" class="level-label">Lv.{{ member.level }}</span></div>
        </div>
      </div>
      <div v-else-if="!error" class="inline-empty">房间暂未返回成员资料。</div>
      <details v-if="raw" class="raw-response"><summary>原始响应</summary><pre>{{ JSON.stringify(raw, null, 2) }}</pre></details>
    </template>
  </AppDialog>
</template>
