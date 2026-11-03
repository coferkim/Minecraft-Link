<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertCircle, ArrowRight, ChevronRight, DoorOpen, Gamepad2, LoaderCircle, RefreshCw, Search, Users } from '@lucide/vue'
import { api, extractRoomInfo, findCollection, getErrorMessage, normalizeRoom } from '../api'
import { ensureUpstreamOk, roomEntity } from '../room-utils'
import PlayerAvatar from './PlayerAvatar.vue'

const props = defineProps({ friendRooms: { type: Array, default: () => [] } })
const emit = defineEmits(['open-room'])
const current = ref(null)
const remoteFriends = ref([])
const results = ref([])
const query = ref('')
const tab = ref('friends')
const loading = ref(false)
const searching = ref(false)
const error = ref('')
const searchError = ref('')
const hasSearched = ref(false)

function unique(rooms) { return [...new Map(rooms.filter(room => room?.id).map(room => [room.id, room])).values()] }
function collection(payload) {
  const rows = [payload?.entities, payload?.entity?.rooms, payload?.entity?.res, payload?.data?.rooms, payload?.rooms, payload?.list].find(Array.isArray) || findCollection(payload)
  return rows.map(value => normalizeRoom(extractRoomInfo(value) || value)).filter(room => room.id)
}
const rooms = computed(() => unique([...remoteFriends.value, ...props.friendRooms]))
const visible = computed(() => tab.value === 'results' ? results.value : rooms.value)
const busy = computed(() => tab.value === 'results' ? searching.value : loading.value)

async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  const responses = await Promise.allSettled([api.currentRoom(), api.friendsPlayingRooms()])
  const failures = []
  responses.forEach((response, index) => {
    try {
      if (response.status === 'rejected') throw response.reason
      ensureUpstreamOk(response.value.data)
      if (index === 0) {
        const value = roomEntity(response.value.data)
        const id = value?.rid ?? value?.room_id ?? value?.identifier ?? value?.room_unique_id ?? value?.id
        current.value = id ? normalizeRoom(value) : null
      } else remoteFriends.value = collection(response.value.data)
    } catch (err) { failures.push(getErrorMessage(err, '部分房间暂未更新')) }
  })
  error.value = [...new Set(failures)].join('；')
  loading.value = false
}
async function search() {
  const value = query.value.trim()
  if (!value || searching.value) return
  searching.value = true
  searchError.value = ''
  hasSearched.value = true
  tab.value = 'results'
  results.value = []
  try {
    if (/^\d+$/.test(value)) {
      const { data } = await api.room(value)
      ensureUpstreamOk(data)
      const entity = roomEntity(data)
      const room = entity ? normalizeRoom(entity) : null
      if (!room?.id) throw new Error('没有找到这个房间，房间可能已经结束。')
      results.value = [room]
      emit('open-room', room)
    } else {
      const { data } = await api.searchRooms({ keyword: value, page: 1, size: 20 })
      ensureUpstreamOk(data)
      results.value = collection(data)
    }
  } catch (err) { searchError.value = getErrorMessage(err, '房间查询失败') }
  finally { searching.value = false }
}
onMounted(load)
</script>

<template>
  <section class="rooms-view">
    <form class="discovery-form room-query-form" @submit.prevent="search"><div class="field-heading"><label for="room-search">找到你的下一个世界</label><span>房间号 / 房间名称</span></div><div class="search-action-row"><label class="search-field"><Search :size="18" /><input id="room-search" v-model="query" placeholder="输入房间号或房间名称" autocomplete="off" /></label><button class="button primary" type="submit" :disabled="!query.trim() || searching"><LoaderCircle v-if="searching" class="spin" :size="16" /><ArrowRight v-else :size="16" />{{ searching ? '查询中' : '查询房间' }}</button></div></form>
    <button v-if="current" class="current-room" type="button" @click="emit('open-room', current)"><Gamepad2 :size="22" /><span><small><i class="status-dot online"></i>我正在玩</small><strong>{{ current.name }}</strong></span><code>#{{ current.id }}</code><ChevronRight :size="18" /></button>
    <div class="room-tabs-row"><div class="list-tabs" role="tablist" aria-label="房间分类"><button type="button" role="tab" :aria-selected="tab === 'friends'" :class="{ active: tab === 'friends' }" @click="tab = 'friends'">好友房间<span>{{ rooms.length }}</span></button><button v-if="hasSearched" type="button" role="tab" :aria-selected="tab === 'results'" :class="{ active: tab === 'results' }" @click="tab = 'results'">搜索结果<span>{{ results.length }}</span></button></div><button v-if="tab === 'friends'" class="icon-button" type="button" title="刷新房间" aria-label="刷新房间" :disabled="loading" @click="load"><RefreshCw :size="16" :class="{ spin: loading }" /></button></div>
    <div v-if="(tab === 'results' && searchError) || (tab === 'friends' && error)" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ tab === 'results' ? searchError : error }}</span><button type="button" :disabled="busy" @click="tab === 'results' ? search() : load()">重试</button></div>
    <div v-if="busy && !visible.length" class="room-grid" aria-label="正在加载房间"><div v-for="i in 3" :key="i" class="skeleton room-skeleton"></div></div>
    <div v-else-if="visible.length" class="room-grid"><button v-for="room in visible" :key="room.id" class="room-tile" type="button" @click="emit('open-room', room)"><img v-if="room.cover" :src="room.cover" class="room-cover" alt="" @error="event => event.target.hidden = true" /><div class="room-tile-top"><span class="live-label"><i class="status-dot online"></i>{{ tab === 'friends' ? '好友正在玩' : '联机房间' }}</span><ChevronRight :size="17" /></div><h2>{{ room.name }}</h2><span class="room-tile-id">房间号 <code>{{ room.id }}</code></span><p v-if="room.mapName || room.serverName">{{ room.mapName || room.serverName }}</p><div class="room-tile-footer"><div v-if="room.friends?.length" class="room-friend-stack"><div><PlayerAvatar v-for="friend in room.friends.slice(0, 3)" :key="friend.id" :player="friend" :size="24" /></div><span>{{ room.friends.length }} 位好友</span></div><span v-else class="muted"><Users :size="14" />{{ room.memberCount ?? '—' }}{{ room.maxMembers ? ` / ${room.maxMembers}` : '' }} 人</span><span class="room-tile-action">查看成员<ArrowRight :size="14" /></span></div></button></div>
    <div v-else-if="!busy" class="empty-state room-empty"><DoorOpen :size="32" :stroke-width="1.3" /><h2>{{ tab === 'results' ? '没有找到匹配的房间' : '等待好友开启新的世界' }}</h2><p>{{ tab === 'results' ? '检查房间号或名称，房间也可能已经结束。' : '也可以通过上方的房间号直接查找。' }}</p></div>
  </section>
</template>
