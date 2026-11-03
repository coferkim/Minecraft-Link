<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertCircle, Check, Copy, RefreshCw, ShieldCheck } from '@lucide/vue'
import { api, findCollection, getErrorMessage, normalizeAccountProfile } from '../api'
import { ensureUpstreamOk } from '../room-utils'
import PlayerAvatar from './PlayerAvatar.vue'

const props = defineProps({ mcUserId: { type: String, default: '' } })
const emit = defineEmits(['notify', 'profile-loaded'])
const player = ref(null)
const session = ref(null)
const loading = ref(false)
const error = ref('')
const updatedAt = computed(() => {
  const value = session.value?.updated_at
  if (!value) return '—'
  const number = Number(value)
  const date = new Date(Number.isFinite(number) ? number * (number < 1e12 ? 1000 : 1) : value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('zh-CN', { hour12: false })
})
async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  const failures = []
  const responses = await Promise.allSettled([api.profile(), api.session()])
  responses.forEach((response, index) => {
    try {
      if (response.status === 'rejected') throw response.reason
      const data = response.value.data
      ensureUpstreamOk(data)
      if (index === 0) {
        const source = data.entity ?? data.data?.entity ?? data.data ?? findCollection(data)[0] ?? data
        if (!source || Array.isArray(source) || typeof source !== 'object') throw new Error('账号资料暂未返回')
        const normalized = normalizeAccountProfile(source)
        const identity = source.friend || source.player || source.role || source
        if (!normalized.id && !identity.nickname && !identity.name && !identity.role_name) throw new Error('账号资料暂未返回')
        if (!normalized.id) normalized.id = props.mcUserId
        player.value = normalized
        emit('profile-loaded', normalized)
        if (data.profile_details_warning) failures.push(String(data.profile_details_warning))
      } else if (index === 1) session.value = data
    } catch (err) {
      const message = getErrorMessage(err, ['账号资料读取失败', '会话状态读取失败'][index])
      failures.push(message)
    }
  })
  error.value = [...new Set(failures)].join('；')
  loading.value = false
}
async function copy() {
  try { await navigator.clipboard.writeText(player.value?.id || props.mcUserId); emit('notify', '已复制账号 UID') }
  catch { emit('notify', '复制失败，请手动选择 UID', 'error') }
}
onMounted(load)
</script>

<template>
  <section class="account-view">
    <div class="section-heading collection-heading"><h2>账号概览</h2><button class="button secondary compact" type="button" :disabled="loading" @click="load"><RefreshCw :size="15" :class="{ spin: loading }" />刷新资料</button></div>
    <div v-if="error" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ error }}</span><button type="button" :disabled="loading" @click="load">重试</button></div>
    <div v-if="loading && !player" class="skeleton account-skeleton" aria-label="正在读取账号资料"></div>
    <div v-else-if="player" class="account-profile"><PlayerAvatar :player="player" :size="76" /><div><h2>{{ player.name }}</h2><div class="account-tags"><span v-if="player.level" class="badge">Lv.{{ player.level }}</span><span v-if="player.vip" class="vip-label">VIP</span></div><p>{{ player.signature || '还没有留下个性签名。' }}</p></div></div>
    <div class="account-sections">
      <section aria-label="账号信息"><h3>账号信息</h3><dl class="profile-facts"><div><dt>玩家 UID</dt><dd><code>{{ player?.id || mcUserId || '—' }}</code><button class="icon-button small" type="button" title="复制账号 UID" aria-label="复制账号 UID" @click="copy"><Copy :size="14" /></button></dd></div><div><dt>玩家昵称</dt><dd>{{ player?.name || '—' }}</dd></div><div><dt>账号等级</dt><dd>{{ player?.level ? `Lv.${player.level}` : '—' }}</dd></div></dl></section>
      <section aria-label="会话信息"><h3><ShieldCheck :size="16" />会话信息</h3><dl class="profile-facts"><div><dt>登录状态</dt><dd :class="{ positive: session?.authenticated }"><Check v-if="session?.authenticated" :size="14" />{{ session ? session.authenticated ? '已连接' : '未连接' : '尚未获取' }}</dd></div><div><dt>会话玩家 UID</dt><dd><code>{{ session?.user_id || '—' }}</code></dd></div><div><dt>最近认证</dt><dd>{{ updatedAt }}</dd></div></dl></section>
    </div>
  </section>
</template>
