<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertCircle, Check, Inbox, LoaderCircle, RefreshCw, Search, X } from '@lucide/vue'
import { api, findCollection, getErrorMessage, normalizeFriend } from '../api'
import { ensureUpstreamOk } from '../room-utils'
import AppDialog from './AppDialog.vue'
import PlayerAvatar from './PlayerAvatar.vue'

const emit = defineEmits(['changed', 'notify'])
const requests = ref([])
const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const query = ref('')
const pending = ref(new Set())
const actionErrors = ref({})
const rejectTarget = ref(null)
const visible = computed(() => {
  const text = query.value.trim().toLowerCase()
  return requests.value.filter(request => [request.player.name, request.player.id, request.message].some(value => value.toLowerCase().includes(text)))
})

async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.friendRequests()
    ensureUpstreamOk(data)
    const rows = findCollection(data)
    requests.value = rows.map(raw => {
      const source = raw.friend || raw.player || raw.role || raw.user || raw
      const id = source.entity_id ?? source.role_id ?? source.user_id ?? source.player_id ?? source.uid ?? source.id ?? raw.fid ?? raw.target_role_id ?? raw.friend_id
      return { player: normalizeFriend({ ...source, id }), message: String(raw.verify_msg || raw.message || raw.msg || ''), raw }
    }).filter(request => request.player.id)
    loaded.value = true
    if (rows.length && !requests.value.length) error.value = '申请数据未包含可识别的玩家 UID，暂时无法处理。'
  } catch (err) { error.value = getErrorMessage(err, '好友申请读取失败') }
  finally { loading.value = false }
}
async function reply(request, agree) {
  const id = request.player.id
  if (loading.value || pending.value.has(id)) return
  pending.value = new Set([...pending.value, id])
  delete actionErrors.value[id]
  try {
    const { data } = await api.replyFriendRequest(id, agree)
    ensureUpstreamOk(data)
    requests.value = requests.value.filter(item => item.player.id !== id)
    if (rejectTarget.value?.player.id === id) rejectTarget.value = null
    emit('notify', agree ? '已通过好友申请' : '已拒绝好友申请')
    if (agree) emit('changed')
  } catch (err) { actionErrors.value[id] = getErrorMessage(err, '处理失败，请重试') }
  finally { pending.value = new Set([...pending.value].filter(value => value !== id)) }
}
onMounted(load)
</script>

<template>
  <section class="requests-view">
    <div class="section-heading collection-heading"><h2>待处理申请 <span class="count-label">{{ loaded ? requests.length : '—' }}</span></h2><button class="button secondary compact" type="button" :disabled="loading || pending.size > 0" @click="load"><RefreshCw :size="15" :class="{ spin: loading }" />刷新申请</button></div>
    <div class="list-toolbar"><label class="search-field"><Search :size="16" /><input v-model="query" placeholder="搜索申请人或验证消息" aria-label="搜索好友申请" /></label><span class="request-count">{{ visible.length }} 条申请</span></div>
    <div v-if="error" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ error }}</span><button type="button" :disabled="loading" @click="load">重试</button></div>
    <div v-if="loading && !loaded" class="friend-skeletons" aria-label="正在读取好友申请"><div v-for="i in 3" :key="i" class="skeleton player-skeleton"></div></div>
    <div v-else-if="visible.length" class="request-list">
      <article v-for="request in visible" :key="request.player.id" class="request-row">
        <PlayerAvatar :player="request.player" :size="44" />
        <div class="request-identity"><strong>{{ request.player.name }}</strong><code>{{ request.player.id }}</code><p>{{ request.message || '未留下验证消息' }}</p><p v-if="actionErrors[request.player.id]" class="form-error" role="alert">{{ actionErrors[request.player.id] }}</p></div>
        <div class="request-actions"><button class="button secondary compact" type="button" :aria-label="`拒绝 ${request.player.name} 的申请`" :disabled="loading || pending.has(request.player.id)" @click="rejectTarget = request"><X :size="15" />拒绝</button><button class="button primary compact" type="button" :aria-label="`通过 ${request.player.name} 的申请`" :disabled="loading || pending.has(request.player.id)" @click="reply(request, true)"><LoaderCircle v-if="pending.has(request.player.id)" :size="15" class="spin" /><Check v-else :size="15" />通过</button></div>
      </article>
    </div>
    <div v-else-if="!error && loaded" class="empty-state"><Inbox :size="32" :stroke-width="1.3" /><h2>{{ query ? '没有匹配的申请' : '所有相遇，都值得期待' }}</h2><p>{{ query ? '换个昵称、UID 或验证消息试试。' : '暂时没有待处理的好友申请。' }}</p><button v-if="query" class="button secondary" type="button" @click="query = ''">清除搜索</button></div>
    <AppDialog :open="Boolean(rejectTarget)" title="拒绝好友申请" :busy="Boolean(rejectTarget && pending.has(rejectTarget.player.id))" @close="rejectTarget = null"><p class="dialog-description">确定拒绝「{{ rejectTarget?.player.name }}」的好友申请吗？</p><p v-if="rejectTarget && actionErrors[rejectTarget.player.id]" class="form-error" role="alert">{{ actionErrors[rejectTarget.player.id] }}</p><template #footer><button class="button secondary" type="button" :disabled="rejectTarget && pending.has(rejectTarget.player.id)" @click="rejectTarget = null">取消</button><button class="button danger" type="button" :disabled="!rejectTarget || pending.has(rejectTarget.player.id)" @click="reply(rejectTarget, false)"><X :size="15" />确认拒绝</button></template></AppDialog>
  </section>
</template>
