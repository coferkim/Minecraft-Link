<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { AlertCircle, ArrowDownWideNarrow, ArrowRight, BookOpen, Check, ChevronRight, Copy, DoorOpen, FileCode2, Gamepad2, Inbox, Info, LoaderCircle, LogOut, Menu, Pencil, RefreshCw, Search, ShieldCheck, Trash2, UserPlus, UserRound, Users, X } from '@lucide/vue'
import { api, findCollection, getErrorMessage, normalizeAccountProfile, normalizeFriend } from '../api'
import { ensureUpstreamOk } from '../room-utils'
import BrandMark from './BrandMark.vue'
import PlayerAvatar from './PlayerAvatar.vue'
import AppDialog from './AppDialog.vue'
import RoomDetails from './RoomDetails.vue'
import RoomsPanel from './RoomBrowser.vue'
import ApiDocs from './ApiDocs.vue'
import FriendRequests from './FriendRequests.vue'
import AccountOverview from './AccountOverview.vue'
import AboutView from './AboutView.vue'

const props = defineProps({ mcUserId: { type: String, default: '' } })
const emit = defineEmits(['logout'])
const views = [
  { id: 'friends', name: '我的好友', icon: Users, description: '在这里，找到一起冒险的人。' },
  { id: 'search', name: '发现玩家', icon: Search, description: '寻找新朋友，也找到下一场冒险。' },
  { id: 'requests', name: '好友申请', icon: Inbox, description: '查看验证消息，处理新的好友申请。' },
  { id: 'rooms', name: '联机房间', icon: DoorOpen, description: '看看好友在哪个世界，或者查找一个房间。' },
  { id: 'account', name: '我的账号', icon: UserRound, description: '查看账号资料与登录状态。' },
  { id: 'docs', name: 'API 文档', icon: FileCode2, description: '接口、参数与返回结果，一处查阅。' },
  { id: 'about', name: '关于我', icon: Info, description: 'FerKim 与 Minecraft 客户端桥接器。' },
]
const activeView = ref(views.some(v => v.id === location.hash.slice(1)) ? location.hash.slice(1) : 'friends')
const view = computed(() => views.find(v => v.id === activeView.value) || views[0])
const mobileNav = ref(false)
const accountPlayer = ref(null)
const accountLoading = ref(false)
const accountError = ref('')
const friends = ref([])
const details = ref([])
const loading = ref(false)
const error = ref('')
const detailError = ref('')
const lastSynced = ref('')
const filter = ref('all')
const query = ref('')
const selected = ref(null)
const selectedRoom = ref(null)
const searchMode = ref('name')
const searchText = ref('')
const searchLoading = ref(false)
const searchResults = ref([])
const searchError = ref('')
const hasSearched = ref(false)
const addTarget = ref(null)
const addMessage = ref('')
const adding = ref(false)
const addError = ref('')
const removeTarget = ref(null)
const removing = ref(false)
const removeError = ref('')
const markTarget = ref(null)
const markText = ref('')
const marking = ref(false)
const markError = ref('')
const marks = ref(new Map())
const toast = ref(null)
let toastTimer
let searchRequest = 0
let accountRequest = 0

const detailById = computed(() => new Map(details.value.map(friend => [friend.id, friend])))
const allFriends = computed(() => friends.value.map(friend => {
  const detail = detailById.value.get(friend.id)
  const player = detail ? normalizeFriend({ ...friend.raw, ...detail.raw }) : friend
  return { ...player, ...(marks.value.has(friend.id) ? { mark: marks.value.get(friend.id) } : {}), isFriend: true }
}))
const friendIds = computed(() => allFriends.value.map(friend => friend.id))
const friendSet = computed(() => new Set(friendIds.value))
const onlineCount = computed(() => allFriends.value.filter(friend => friend.online === true).length)
const playingCount = computed(() => allFriends.value.filter(friend => friend.room?.id).length)
const friendRooms = computed(() => {
  const rooms = new Map()
  for (const friend of allFriends.value) {
    if (!friend.room?.id) continue
    if (!rooms.has(friend.room.id)) rooms.set(friend.room.id, { ...friend.room, friends: [] })
    rooms.get(friend.room.id).friends.push(friend)
  }
  return [...rooms.values()]
})
const filteredFriends = computed(() => {
  const text = query.value.trim().toLowerCase()
  return allFriends.value.filter(friend => {
    if (filter.value === 'online' && friend.online !== true) return false
    if (filter.value === 'playing' && !friend.room?.id) return false
    return !text || [friend.name, friend.mark, friend.id, friend.room?.name, friend.signature].some(value => String(value || '').toLowerCase().includes(text))
  }).sort(sortPlayers)
})
const profile = computed(() => selected.value && (allFriends.value.find(friend => friend.id === selected.value.id) || selected.value))

function sortPlayers(a, b) {
  const rank = player => player.online === true ? 0 : player.online === null ? 1 : 2
  return rank(a) - rank(b) || Number(Boolean(b.room?.id)) - Number(Boolean(a.room?.id)) || a.name.localeCompare(b.name, 'zh-CN')
}
function notify(message, kind = 'success') {
  clearTimeout(toastTimer)
  toast.value = { message, kind }
  toastTimer = setTimeout(() => { toast.value = null }, 3000)
}
function navigate(id) { activeView.value = id; mobileNav.value = false }
function onHash() { if (views.some(v => v.id === location.hash.slice(1))) navigate(location.hash.slice(1)) }
watch(activeView, id => { history.replaceState(null, '', `#${id}`) })

async function loadAccount() {
  if (accountLoading.value) return
  accountLoading.value = true
  accountError.value = ''
  const version = ++accountRequest
  try {
    const { data } = await api.profile()
    if (version !== accountRequest) return
    ensureUpstreamOk(data)
    const source = data.entity ?? data.data?.entity ?? data.data ?? findCollection(data)[0] ?? data
    const player = normalizeAccountProfile(source)
    if (!player.id) throw new Error('账号资料暂未返回')
    accountPlayer.value = player
  } catch (err) { if (version === accountRequest) accountError.value = getErrorMessage(err, '账号资料读取失败') }
  finally { if (version === accountRequest) accountLoading.value = false }
}
function updateAccount(player) { accountRequest++; accountPlayer.value = player; accountError.value = ''; accountLoading.value = false }

async function loadFriends() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  detailError.value = ''
  try {
    const response = await api.friends()
    ensureUpstreamOk(response.data)
    friends.value = findCollection(response.data).map(normalizeFriend).filter(friend => friend.id)
    try {
      const response = await api.friendDetails()
      ensureUpstreamOk(response.data)
      details.value = findCollection(response.data).map(normalizeFriend).filter(friend => friend.id)
    } catch (err) { detailError.value = getErrorMessage(err, '部分好友资料暂未更新') }
    lastSynced.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch (err) { error.value = getErrorMessage(err, '好友列表加载失败') }
  finally { loading.value = false }
}
async function runSearch() {
  const text = searchText.value.trim()
  if (!text || searchLoading.value) return
  if (searchMode.value === 'id' && !/^\d+$/.test(text)) { searchError.value = 'UID 需要填写数字'; return }
  const version = ++searchRequest
  searchLoading.value = true
  searchError.value = ''
  hasSearched.value = true
  try {
    const { data } = await api.search(searchMode.value === 'id' ? { user_id: text } : { name: text })
    ensureUpstreamOk(data)
    if (version !== searchRequest) return
    searchResults.value = findCollection(data).map(normalizeFriend).filter(player => player.id).sort(sortPlayers)
  } catch (err) { if (version === searchRequest) { searchResults.value = []; searchError.value = getErrorMessage(err, '玩家搜索失败') } }
  finally { if (version === searchRequest) searchLoading.value = false }
}
function openRoom(room) { selected.value = null; selectedRoom.value = room }
function beginAdd(player) { selected.value = null; addTarget.value = player; addMessage.value = ''; addError.value = '' }
async function submitAdd() {
  if (!addTarget.value || adding.value) return
  adding.value = true
  addError.value = ''
  try {
    const { data } = await api.addFriend({ target_id: addTarget.value.id, message: addMessage.value.trim() })
    ensureUpstreamOk(data)
    addTarget.value = null
    notify('好友请求已发送')
  } catch (err) { addError.value = getErrorMessage(err, '好友请求发送失败') }
  finally { adding.value = false }
}
function beginRemove(player) { selected.value = null; removeTarget.value = player; removeError.value = '' }
async function submitRemove() {
  if (!removeTarget.value || removing.value) return
  removing.value = true
  removeError.value = ''
  try {
    const { data } = await api.removeFriend(removeTarget.value.id)
    ensureUpstreamOk(data)
    friends.value = friends.value.filter(friend => friend.id !== removeTarget.value.id)
    removeTarget.value = null
    notify('好友已删除')
  } catch (err) { removeError.value = getErrorMessage(err, '删除好友失败') }
  finally { removing.value = false }
}
function beginMark(player) {
  selected.value = null
  markTarget.value = player
  markText.value = player.mark || ''
  markError.value = ''
}
async function submitMark() {
  if (!markTarget.value || marking.value) return
  marking.value = true
  markError.value = ''
  try {
    const mark = markText.value.trim()
    const { data } = await api.markFriend(markTarget.value.id, mark)
    ensureUpstreamOk(data)
    marks.value.set(markTarget.value.id, mark)
    markTarget.value = null
    notify(mark ? '好友备注已保存' : '好友备注已清除')
  } catch (err) { markError.value = getErrorMessage(err, '备注保存失败') }
  finally { marking.value = false }
}
async function copy(value) {
  try { await navigator.clipboard.writeText(String(value)); notify('已复制玩家 UID') }
  catch { notify('复制失败，请手动选择 UID', 'error') }
}
function formatTime(value) {
  if (!value) return '—'
  const date = new Date(Number(value) > 1e12 ? Number(value) : Number(value) * 1000)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
}
onMounted(() => { loadFriends(); loadAccount(); window.addEventListener('hashchange', onHash) })
onUnmounted(() => { clearTimeout(toastTimer); searchRequest++; accountRequest++; window.removeEventListener('hashchange', onHash) })
</script>

<template>
  <div class="console-shell">
    <aside class="sidebar">
      <BrandMark />
      <span class="nav-group-label">工作空间</span>
      <nav class="sidebar-nav" aria-label="主导航">
        <button v-for="item in views" :key="item.id" type="button" :class="{ active: activeView === item.id }" :aria-current="activeView === item.id ? 'page' : undefined" @click="navigate(item.id)"><component :is="item.icon" :size="18" /><span>{{ item.name }}</span><ChevronRight v-if="activeView === item.id" :size="14" /></button>
      </nav>
      <div class="sidebar-bottom">
        <div class="session-state"><span class="status-dot online"></span><span>账号已连接</span><ShieldCheck :size="14" /></div>
        <div class="account-row"><button class="account-identity" type="button" :title="accountPlayer?.name || '查看我的账号'" aria-label="查看我的账号" @click="navigate('account')"><PlayerAvatar v-if="accountPlayer" :player="accountPlayer" :size="34" /><span v-else class="account-symbol"><LoaderCircle v-if="accountLoading" :size="18" class="spin" /><UserRound v-else :size="18" /></span><span class="account-copy"><strong>{{ accountPlayer?.name || (accountLoading ? '正在读取账号' : '资料暂不可用') }}</strong><code>{{ accountPlayer?.id || mcUserId || '—' }}</code></span></button><button v-if="accountError" class="icon-button" type="button" :title="accountError" aria-label="重试读取账号资料" :disabled="accountLoading" @click="loadAccount"><RefreshCw :size="15" :class="{ spin: accountLoading }" /></button><button class="icon-button" type="button" title="退出登录" aria-label="退出登录" @click="emit('logout')"><LogOut :size="17" /></button></div>
      </div>
    </aside>
    <main class="workspace">
      <header class="topbar">
        <button class="icon-button mobile-menu" type="button" title="打开导航" aria-label="打开导航" @click="mobileNav = true"><Menu :size="21" /></button>
        <div class="breadcrumb"><span>Minecraft Link</span><ChevronRight :size="13" /><strong>{{ view.name }}</strong></div>
        <div class="topbar-session"><span class="status-dot online"></span>本地会话<span class="topbar-divider"></span><ShieldCheck :size="15" /><span>已认证</span></div>
      </header>
      <div class="workspace-body">
        <header class="page-heading"><div><h1>{{ view.name }}</h1><p>{{ view.description }}</p></div><button v-if="activeView === 'friends'" class="button primary" type="button" @click="navigate('search')"><UserPlus :size="16" />添加好友</button></header>
        <section v-show="activeView === 'friends'" class="friends-view">
          <div class="metrics-strip">
            <div><span>全部好友</span><strong>{{ allFriends.length }}<small>位</small></strong></div>
            <div><span><i class="status-dot online"></i>当前在线</span><strong>{{ onlineCount }}<small>位</small></strong></div>
            <div><span>正在联机</span><strong>{{ playingCount }}<small>位</small></strong></div>
            <div class="metrics-sync"><RefreshCw :size="14" :class="{ spin: loading }" /><span>{{ loading ? '正在同步好友' : lastSynced ? `${lastSynced} 更新` : '尚未同步' }}</span></div>
          </div>
          <div class="social-layout">
            <section class="friends-main" aria-label="好友列表">
              <div class="list-tabs" role="tablist" aria-label="好友筛选">
                <button v-for="tab in [{ id: 'all', label: '全部好友', count: allFriends.length }, { id: 'online', label: '在线', count: onlineCount }, { id: 'playing', label: '正在联机', count: playingCount }]" :key="tab.id" role="tab" type="button" :aria-selected="filter === tab.id" :class="{ active: filter === tab.id }" @click="filter = tab.id">{{ tab.label }}<span>{{ tab.count }}</span></button>
              </div>
              <div class="list-toolbar"><label class="search-field"><Search :size="16" /><input v-model="query" placeholder="搜索昵称、UID 或房间" aria-label="搜索好友" /><button v-if="query" type="button" class="icon-button small" aria-label="清除搜索" @click="query = ''"><X :size="14" /></button></label><span class="sort-label"><ArrowDownWideNarrow :size="14" />在线优先</span><button class="icon-button" type="button" title="刷新好友" aria-label="刷新好友" :disabled="loading" @click="loadFriends"><RefreshCw :size="16" :class="{ spin: loading }" /></button></div>
              <div v-if="error || detailError" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ error || detailError }}</span><button type="button" :disabled="loading" @click="loadFriends">重试</button></div>
              <div class="friend-table-head"><span>玩家</span><span>状态</span><span>游戏动态</span><span></span></div>
              <div v-if="loading && !allFriends.length" class="friend-skeletons" aria-label="正在加载好友"><div v-for="i in 6" :key="i" class="skeleton player-skeleton"></div></div>
              <div v-else-if="!filteredFriends.length && !error" class="empty-state"><Users :size="30" :stroke-width="1.4" /><h2>{{ query || filter !== 'all' ? '没有匹配的好友' : '好友列表还是空的' }}</h2><p>{{ query || filter !== 'all' ? '换个昵称或筛选条件试试。' : '从一个熟悉的名字开始，找到一起玩的伙伴。' }}</p><button class="button secondary" type="button" @click="query || filter !== 'all' ? (query = '', filter = 'all') : navigate('search')">{{ query || filter !== 'all' ? '清除筛选' : '发现玩家' }}<ArrowRight :size="15" /></button></div>
              <div v-else class="friend-list">
                <article v-for="friend in filteredFriends" :key="friend.id" class="friend-row">
                  <button class="player-identity" type="button" @click="selected = friend"><PlayerAvatar :player="friend" /><span><strong>{{ friend.mark || friend.name }}<em v-if="friend.vip" class="vip-label">VIP</em></strong><small><code>{{ friend.id }}</code><span v-if="friend.level">Lv.{{ friend.level }}</span></small></span></button>
                  <span class="player-status" :class="{ positive: friend.online === true }"><i class="status-dot" :class="{ online: friend.online === true }"></i>{{ friend.onlineLabel === '未知' ? '状态未知' : friend.onlineLabel }}</span>
                  <button v-if="friend.room?.id" class="activity-link" type="button" @click="openRoom(friend.room)"><Gamepad2 :size="15" /><span><strong>{{ friend.room.name }}</strong><small>房间 {{ friend.room.id }}</small></span><ChevronRight :size="14" /></button>
                  <span v-else class="no-activity">{{ friend.online === true ? '在大厅中' : '暂无公开游戏动态' }}</span>
                  <button class="icon-button row-detail" type="button" :aria-label="`查看 ${friend.name} 的资料`" title="查看玩家资料" @click="selected = friend"><ChevronRight :size="17" /></button>
                </article>
              </div>
              <div class="list-footer"><span>{{ filteredFriends.length }} 位好友</span><span>在线好友优先显示</span></div>
            </section>
            <aside class="activity-rail">
              <div class="section-heading"><h2><Gamepad2 :size="16" />好友正在玩</h2><span class="count-label">{{ friendRooms.length }} 个房间</span></div>
              <button v-for="room in friendRooms.slice(0, 5)" :key="room.id" class="live-room" type="button" @click="openRoom(room)"><div class="live-room-top"><span class="live-label"><i class="status-dot online"></i>联机中</span><code>#{{ room.id }}</code><ChevronRight :size="15" /></div><strong>{{ room.name }}</strong><div class="room-friend-stack"><div><PlayerAvatar v-for="friend in room.friends.slice(0, 3)" :key="friend.id" :player="friend" :size="24" /></div><span>{{ room.friends.map(friend => friend.mark || friend.name).slice(0, 2).join('、') }}{{ room.friends.length > 2 ? ` 等 ${room.friends.length} 位好友` : '' }}</span></div></button>
              <div v-if="!friendRooms.length" class="rail-empty"><DoorOpen :size="26" :stroke-width="1.3" /><strong>好友的世界，等你加入</strong><p>还没有好友公开正在玩的房间。</p></div>
              <button class="text-link rail-link" type="button" @click="navigate('rooms')">前往联机房间<ArrowRight :size="14" /></button>
              <div class="rail-docs"><BookOpen :size="19" :stroke-width="1.5" /><h3>让连接更进一步</h3><p>查阅 Minecraft Link 的接口与数据。</p><button class="text-link" type="button" @click="navigate('docs')">打开 API 文档<ArrowRight :size="14" /></button></div>
            </aside>
          </div>
        </section>
        <section v-show="activeView === 'search'" class="discover-view">
          <form class="discovery-form" @submit.prevent="runSearch"><div class="field-heading"><label for="player-search">查找玩家</label><div class="segmented" role="group" aria-label="搜索方式"><button type="button" :aria-pressed="searchMode === 'name'" :class="{ active: searchMode === 'name' }" @click="searchMode = 'name'">昵称 / 邮箱</button><button type="button" :aria-pressed="searchMode === 'id'" :class="{ active: searchMode === 'id' }" @click="searchMode = 'id'">UID</button></div></div><div class="search-action-row"><label class="search-field"><Search :size="18" /><input id="player-search" v-model="searchText" :placeholder="searchMode === 'id' ? '输入玩家 UID' : '输入玩家昵称或邮箱'" :inputmode="searchMode === 'id' ? 'numeric' : 'text'" autocomplete="off" /></label><button class="button primary" type="submit" :disabled="!searchText.trim() || searchLoading"><LoaderCircle v-if="searchLoading" :size="16" class="spin" /><Search v-else :size="16" />{{ searchLoading ? '查找中' : '查找玩家' }}</button></div></form>
          <div v-if="searchError" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ searchError }}</span></div>
          <div v-if="searchLoading" class="friend-skeletons" aria-label="正在搜索"><div v-for="i in 3" :key="i" class="skeleton player-skeleton"></div></div>
          <template v-else-if="searchResults.length"><div class="section-heading results-heading"><h2>搜索结果</h2><span>{{ searchResults.length }} 位玩家</span></div><div class="discovery-grid"><article v-for="player in searchResults" :key="player.id" class="discovery-player"><div class="discovery-player-head"><button class="player-identity" type="button" @click="selected = player"><PlayerAvatar :player="player" :size="48" show-status /><span><strong>{{ player.name }}</strong><small><code>{{ player.id }}</code><span v-if="player.level">Lv.{{ player.level }}</span></small></span></button><span v-if="friendSet.has(player.id)" class="badge positive">好友</span></div><p>{{ player.signature || '这个玩家还没有留下签名。' }}</p><button v-if="player.room?.id" class="activity-link discovery-activity" type="button" @click="openRoom(player.room)"><Gamepad2 :size="16" /><span><strong>{{ player.room.name }}</strong><small>房间 {{ player.room.id }}</small></span><ChevronRight :size="15" /></button><div v-else class="discovery-activity no-activity"><Gamepad2 :size="16" />暂无公开房间</div><div class="discovery-actions"><span class="player-status" :class="{ positive: player.online === true }"><i class="status-dot" :class="{ online: player.online === true }"></i>{{ player.onlineLabel }}</span><button class="button secondary compact" type="button" :disabled="friendSet.has(player.id) || player.id === props.mcUserId" @click="beginAdd(player)"><Check v-if="friendSet.has(player.id)" :size="14" /><UserPlus v-else :size="14" />{{ friendSet.has(player.id) ? '已是好友' : player.id === props.mcUserId ? '这是你' : '加好友' }}</button></div></article></div></template>
          <div v-else-if="!searchError" class="empty-state discover-empty"><Search :size="32" :stroke-width="1.3" /><h2>{{ hasSearched ? '没有找到这位玩家' : '下一个队友，或许就在这里' }}</h2><p>{{ hasSearched ? '检查昵称或 UID，换个关键词再试一次。' : '输入昵称、邮箱或 UID，找到玩家和他们正在玩的房间。' }}</p></div>
        </section>
        <KeepAlive><RoomsPanel v-if="activeView === 'rooms'" :friend-rooms="friendRooms" @open-room="openRoom" /></KeepAlive>
        <FriendRequests v-if="activeView === 'requests'" @changed="loadFriends" @notify="notify" />
        <AccountOverview v-if="activeView === 'account'" :mc-user-id="mcUserId" @profile-loaded="updateAccount" @notify="notify" />
        <KeepAlive><ApiDocs v-if="activeView === 'docs'" /></KeepAlive>
        <AboutView v-if="activeView === 'about'" @navigate="navigate" />
        <footer class="workspace-footer"><BrandMark compact /><span>Minecraft Link</span><span class="footer-version">社交控制台 / v1.0</span></footer>
      </div>
    </main>
    <AppDialog :open="mobileNav" title="Minecraft Link" subtitle="工作空间" @close="mobileNav = false"><nav class="mobile-nav" aria-label="移动端导航"><button v-for="item in views" :key="item.id" type="button" :class="{ active: activeView === item.id }" @click="navigate(item.id)"><component :is="item.icon" :size="20" />{{ item.name }}<ChevronRight :size="16" /></button></nav><button class="button secondary wide" type="button" @click="emit('logout')"><LogOut :size="16" />退出登录</button></AppDialog>
    <AppDialog :open="Boolean(profile)" title="玩家资料" subtitle="我的世界 · 中国版" drawer @close="selected = null">
      <template v-if="profile"><div class="profile-heading"><PlayerAvatar :player="profile" :size="76" show-status /><h3>{{ profile.mark || profile.name }}</h3><div class="profile-tags"><span class="player-status" :class="{ positive: profile.online === true }"><i class="status-dot" :class="{ online: profile.online === true }"></i>{{ profile.onlineLabel }}</span><span v-if="profile.level" class="badge">Lv.{{ profile.level }}</span><span v-if="profile.vip" class="vip-label">VIP</span><span v-if="friendSet.has(profile.id)" class="badge">我的好友</span></div><p>{{ profile.signature || '还没有留下个性签名。' }}</p></div><dl class="profile-facts"><div><dt>玩家 UID</dt><dd><code>{{ profile.id }}</code><button class="icon-button small" type="button" title="复制 UID" aria-label="复制 UID" @click="copy(profile.id)"><Copy :size="14" /></button></dd></div><div><dt>玩家昵称</dt><dd>{{ profile.name }}</dd></div><div><dt>最近在线</dt><dd>{{ formatTime(profile.lastSeen) }}</dd></div><div><dt>亲密值</dt><dd>{{ profile.intimacy }}</dd></div></dl><div class="section-heading"><h3>游戏动态</h3></div><button v-if="profile.room?.id" class="profile-room" type="button" @click="openRoom(profile.room)"><Gamepad2 :size="21" /><div><strong>{{ profile.room.name }}</strong><small>房间 {{ profile.room.id }}</small></div><ChevronRight :size="17" /></button><div v-else class="inline-empty">暂无公开的房间动态。</div><div class="profile-actions"><button v-if="friendSet.has(profile.id)" class="button secondary" type="button" @click="beginMark(profile)"><Pencil :size="15" />编辑备注</button><button v-if="!friendSet.has(profile.id) && profile.id !== mcUserId" class="button primary" type="button" @click="beginAdd(profile)"><UserPlus :size="16" />添加好友</button><button v-if="friendSet.has(profile.id)" class="button danger" type="button" @click="beginRemove(profile)"><Trash2 :size="15" />删除好友</button></div><details class="raw-response"><summary>玩家原始数据</summary><pre>{{ JSON.stringify(profile.raw, null, 2) }}</pre></details></template>
    </AppDialog>
    <RoomDetails :room="selectedRoom" :friend-ids="friendIds" @close="selectedRoom = null" />
    <AppDialog :open="Boolean(markTarget)" title="编辑好友备注" :subtitle="markTarget?.name" :busy="marking" @close="markTarget = null"><form id="friend-mark-form" @submit.prevent="submitMark"><label class="field-label" for="friend-mark">好友备注 <span>{{ markText.length }} / 100</span></label><div class="search-field"><Pencil :size="16" /><input id="friend-mark" v-model="markText" maxlength="100" placeholder="留空则恢复显示玩家昵称" /></div><p v-if="markError" class="form-error" role="alert">{{ markError }}</p></form><template #footer><button class="button secondary" type="button" :disabled="marking" @click="markTarget = null">取消</button><button class="button primary" type="submit" form="friend-mark-form" :disabled="marking"><LoaderCircle v-if="marking" :size="16" class="spin" /><Check v-else :size="16" />{{ marking ? '保存中' : '保存备注' }}</button></template></AppDialog>
    <AppDialog :open="Boolean(addTarget)" title="添加好友" :subtitle="addTarget?.name" :busy="adding" @close="addTarget = null"><form id="add-friend-form" @submit.prevent="submitAdd"><p class="dialog-description">向 {{ addTarget?.name }} 发送好友请求，认识新的伙伴。</p><label class="field-label" for="add-message">验证消息 <span>可选</span></label><textarea id="add-message" v-model="addMessage" class="text-area" placeholder="一起玩我的世界吧！" maxlength="120"></textarea><p v-if="addError" class="form-error" role="alert">{{ addError }}</p></form><template #footer><button class="button secondary" type="button" :disabled="adding" @click="addTarget = null">取消</button><button class="button primary" type="submit" form="add-friend-form" :disabled="adding"><LoaderCircle v-if="adding" :size="16" class="spin" /><UserPlus v-else :size="16" />{{ adding ? '发送中' : '发送请求' }}</button></template></AppDialog>
    <AppDialog :open="Boolean(removeTarget)" title="删除好友" :busy="removing" @close="removeTarget = null"><p class="dialog-description">确定从好友列表中移除「{{ removeTarget?.name }}」吗？再次成为好友需要重新发送请求。</p><p v-if="removeError" class="form-error" role="alert">{{ removeError }}</p><template #footer><button class="button secondary" type="button" :disabled="removing" @click="removeTarget = null">取消</button><button class="button danger" type="button" :disabled="removing" @click="submitRemove"><LoaderCircle v-if="removing" :size="16" class="spin" /><Trash2 v-else :size="16" />{{ removing ? '删除中' : '确认删除' }}</button></template></AppDialog>
    <Teleport to="body"><Transition name="toast"><div v-if="toast" class="toast" :class="toast.kind" role="status"><Check v-if="toast.kind === 'success'" :size="17" /><AlertCircle v-else :size="17" /><span>{{ toast.message }}</span></div></Transition></Teleport>
  </div>
</template>
