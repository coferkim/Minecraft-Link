import axios from 'axios'

export const DEFAULT_API_BASE = '/api'

export function getApiBaseUrl() {
  return DEFAULT_API_BASE
}

export const http = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 45000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/authorize/')) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('mc_user_id')
      window.dispatchEvent(new CustomEvent('mc-session-expired'))
    }
    return Promise.reject(error)
  },
)

export function getErrorMessage(error, fallback = '请求失败，请稍后再试') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => item.msg || String(item)).join('；')
  }
  if (error?.code === 'ECONNABORTED') return '请求超时，请检查网络或上游服务状态'
  if (!error?.response && error?.message) {
    return error?.isAxiosError ? `无法连接后端：${error.message}` : error.message
  }
  return fallback
}

export function isImageUrl(value) {
  const text = String(value || '').trim()
  if (!text) return false
  return /^(https?:\/\/|data:image\/|blob:|\/|\.\/|\.\.\/)/i.test(text)
}

function playerAvatar(source) {
  return [source.headImage, source.head_image, source.avatar_image_url, source.avatar,
    source.static_url, source.head_img, source.head_url, source.dynamic_head_img, source.avatar_url]
    .find(isImageUrl) || ''
}

export function unwrapSauth(text) {
  let value
  try {
    value = JSON.parse(text)
  } catch {
    throw new Error('内容不是合法 JSON，请粘贴完整的 sauth 对象')
  }
  if (typeof value?.sauth_json === 'string') {
    try {
      value = JSON.parse(value.sauth_json)
    } catch {
      throw new Error('sauth_json 字段不是合法 JSON')
    }
  } else if (value?.sauth_json && typeof value.sauth_json === 'object') {
    value = value.sauth_json
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('sauth 必须是一个 JSON 对象')
  }
  const missing = ['client_login_sn', 'udid', 'deviceid', 'sdkuid', 'sessionid'].filter(
    (key) => !value[key],
  )
  if (missing.length) {
    throw new Error(`缺少字段：${missing.join('、')}`)
  }
  return value
}

export function findCollection(payload) {
  if (Array.isArray(payload)) return payload
  if (!payload || typeof payload !== 'object') return []

  const queue = [{ value: payload, depth: 0 }]
  const preferred = [
    'friends',
    'friend_list',
    'all_friends',
    'list',
    'items',
    'roles',
    'entities',
    'result',
    'data',
  ]
  while (queue.length) {
    const { value, depth } = queue.shift()
    if (Array.isArray(value)) return value
    if (!value || typeof value !== 'object' || depth > 3) continue
    for (const key of preferred) {
      if (Array.isArray(value[key])) return value[key]
    }
    for (const child of Object.values(value)) {
      if (child && typeof child === 'object') queue.push({ value: child, depth: depth + 1 })
    }
  }
  return []
}

export function normalizeFriend(item) {
  const source = item?.friend || item?.player || item?.role || item || {}
  const gameState = source.game_state || source.state || {}
  const id =
    source.entity_id ??
    source.role_id ??
    source.user_id ??
    source.player_id ??
    source.uid ??
    source.id ??
    ''
  const name =
    source.name ??
    source.nickname ??
    source.player_name ??
    source.role_name ??
    source.display_name ??
    source.username ??
    `玩家 ${id || '未知'}`
  const online = parseOnlineState(source, gameState)
  const growth = source.pe_growth || source.growth || {}
  const vipLevel = Number(source.recharge_vip_level ?? growth.vip_level ?? 0)
  const frameCandidate =
    source.frame_url ||
    source.frameUrl ||
    source.frame_image ||
    source.frameImage ||
    source.avatar_frame_url ||
    source.avatarFrameUrl ||
    (isImageUrl(source.frame_id) ? source.frame_id : '') ||
    (isImageUrl(source.frameId) ? source.frameId : '') ||
    source.frame ||
    source.avatar_frame ||
    source.avatarFrame ||
    ''
  const frameId =
    (!isImageUrl(source.frame_id) ? source.frame_id : '') ||
    (!isImageUrl(source.frameId) ? source.frameId : '') ||
    source.avatar_frame_id ||
    source.avatarFrameId ||
    (!isImageUrl(frameCandidate) ? frameCandidate : '')
  const room = extractRoomInfo(source)
  return {
    ...source,
    id: String(id),
    name: String(name),
    avatar: playerAvatar(source),
    frame: isImageUrl(frameCandidate) ? frameCandidate : '',
    frameId: String(frameId || ''),
    online,
    onlineLabel: online === true ? '在线' : online === false ? '离线' : '未知',
    level: Number(growth.lv ?? source.level ?? 0) || 0,
    vip: Boolean(growth.is_vip || source.is_vip || vipLevel > 0),
    vipLevel,
    signature: source.signature || source.sign || source.motto || source.intro || '',
    mark: source.mark || source.remark || '',
    room,
    lastSeen: source.tLogout || source.tLogin || source.last_seen || '',
    intimacy: Number(source.intimacy_value ?? 0) || 0,
    isFriend: Boolean(source.is_friend ?? source.isFriend ?? false),
    raw: item,
  }
}

export function normalizeAccountProfile(item) {
  const source = item?.friend || item?.player || item?.role || item || {}
  const player = normalizeFriend(item)
  const level = Number(source.pe_growth?.lv ?? source.growth?.lv)
  return { ...player, level: Number.isFinite(level) && level > 0 ? level : 0 }
}

function parseOnlineState(source, gameState) {
  const direct =
    source.online ??
    source.is_online ??
    source.online_state ??
    gameState.online ??
    gameState.is_online
  if (direct !== undefined && direct !== null) {
    if (typeof direct === 'boolean') return direct
    if (typeof direct === 'number') return direct > 0
    const value = String(direct).trim().toLowerCase()
    if (['0', 'offline', 'off', 'false'].includes(value)) return false
    if (['1', 'online', 'on', 'true'].includes(value)) return true
  }

  const rawStatus = source.online_status
  if (typeof rawStatus === 'boolean') return rawStatus
  if (typeof rawStatus === 'number') return rawStatus > 0
  if (typeof rawStatus === 'string' && rawStatus.trim()) {
    try {
      const parsed = JSON.parse(rawStatus)
      if (parsed && typeof parsed === 'object' && 'status' in parsed) {
        return Number(parsed.status) > 0
      }
    } catch {
      const value = rawStatus.toLowerCase()
      if (['0', 'offline', 'off', 'false'].includes(value)) return false
      if (['1', 'online', 'on', 'true'].includes(value)) return true
    }
  }

  if ('online_pcpe' in source) {
    return Number(source.online_pcpe || 0) > 0
  }

  const login = Number(source.tLogin || 0)
  const logout = Number(source.tLogout || 0)
  if (login && logout) return login > logout
  return null
}

function isRoomLike(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const id =
    value.rid ??
    value.room_id ??
    value.roomId ??
    value.room_unique_id ??
    value.identifier ??
    value.target_room_id ??
    value.transfer_room_id
  const name = value.room_name ?? value.roomName ?? value.slogan ?? value.room_slogan
  return id !== undefined || (name !== undefined && value.room_type !== undefined)
}

export function normalizeRoom(item) {
  let source = item?.room || item?.room_info || item?.game_info || item?.gameInfo || item || {}
  if (Array.isArray(source)) source = source[0] || {}
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      source = {}
    }
  }
  const id =
    source.rid ??
    source.room_id ??
    source.roomId ??
    source.room_unique_id ??
    source.identifier ??
    source.target_room_id ??
    source.transfer_room_id ??
    source.id ??
    ''
  const name =
    source.room_name ??
    source.roomName ??
    source.name ??
    source.slogan ??
    source.room_slogan ??
    source.map_name ??
    `房间 ${id || '未知'}`
  return {
    ...source,
    id: String(id),
    name: String(name),
    ownerId: String(
      source.hid ??
        source.owner_id ??
        source.room_owner_id ??
        source.ownerId ??
        source.room_owner ??
        '',
    ),
    ownerName:
      source.owner_name ??
      source.room_owner_name ??
      source.owner_nickname ??
      source.nickname ??
      '',
    memberCount:
      source.cnt ??
      source.player_count ??
      source.member_count ??
      source.room_player_count ??
      source.current_player_count ??
      null,
    maxMembers: source.cap ?? source.max_player_count ?? source.max_member_count ?? null,
    type: source.room_type ?? source.roomType ?? source.type ?? '',
    mapName: source.room_map_name ?? source.map_name ?? source.level_name ?? '',
    serverName: source.server_name ?? source.serverName ?? '',
    cover: source.room_cover ?? source.room_pic ?? source.cover ?? source.image ?? '',
    raw: item,
  }
}

export function extractRoomInfo(item) {
  const roots = [
    item?.game_info,
    item?.gameInfo,
    item?.room_info,
    item?.roomInfo,
    item?.room,
    item?.current_room,
    item?.currentRoom,
    item?.game_info?.[0],
    item?.game_info?.['game-info'],
    item?.gameInfo?.[0],
    item?.gameInfo?.['game-info'],
  ]
  const queue = roots.filter(Boolean).map((value) => ({ value, depth: 0 }))
  const seen = new Set()
  while (queue.length) {
    const entry = queue.shift()
    let value = entry.value
    const depth = entry.depth
    if (typeof value === 'string') {
      try {
        value = JSON.parse(value)
      } catch {
        continue
      }
    }
    if (!value || typeof value !== 'object' || seen.has(value) || depth > 6) continue
    seen.add(value)
    if (isRoomLike(value)) return normalizeRoom(value)
    if (Array.isArray(value)) {
      queue.push(...value.map((child) => ({ value: child, depth: depth + 1 })))
    } else {
      for (const child of Object.values(value)) {
        if (child && (typeof child === 'object' || typeof child === 'string')) {
          queue.push({ value: child, depth: depth + 1 })
        }
      }
    }
  }
  return null
}

export function normalizeRoomMember(item, index = 0, ownerId = '') {
  const source = item?.player || item?.member || item?.user || item?.role || item || {}
  const gameState = source.game_state || source.state || {}
  const id =
    source.uid ??
    source.player_id ??
    source.role_id ??
    source.entity_id ??
    source.playerId ??
    source.id ??
    ''
  const growth = source.pe_growth || source.growth || {}
  const vipLevel = Number(source.recharge_vip_level ?? growth.vip_level ?? 0)
  const frameCandidate =
    source.frame_url ||
    source.frameUrl ||
    source.frame_image ||
    source.frameImage ||
    source.avatar_frame_url ||
    source.avatarFrameUrl ||
    (isImageUrl(source.frame_id) ? source.frame_id : '') ||
    (isImageUrl(source.frameId) ? source.frameId : '') ||
    source.frame ||
    source.avatar_frame ||
    source.avatarFrame ||
    ''
  const frameId =
    (!isImageUrl(source.frame_id) ? source.frame_id : '') ||
    (!isImageUrl(source.frameId) ? source.frameId : '') ||
    source.avatar_frame_id ||
    source.avatarFrameId ||
    (!isImageUrl(frameCandidate) ? frameCandidate : '')
  const online = parseOnlineState(source, gameState)
  return {
    ...source,
    id: String(id),
    name: String(
      source.nickname ??
        source.name ??
        source.player_name ??
        source.role_name ??
        source.user_name ??
        source.gamerTag ??
        `玩家 ${id || index + 1}`,
    ),
    avatar: playerAvatar(source),
    frame: isImageUrl(frameCandidate) ? frameCandidate : '',
    frameId: String(frameId || ''),
    online,
    onlineLabel: online === true ? '在线' : online === false ? '离线' : '未知',
    level: Number(growth.lv ?? source.level ?? 0) || 0,
    vip: Boolean(growth.is_vip || source.is_vip || vipLevel > 0),
    vipLevel,
    isFriend: Boolean(source.is_friend ?? source.isFriend ?? source.friend ?? false),
    isOwner: Boolean(
      source.is_owner ??
        source.isOwner ??
        source.owner ??
        (ownerId ? String(id) === String(ownerId) : index === 0),
    ),
    raw: item,
  }
}

export const api = {
  health: () => http.get('/healthz'),
  endpoints: () => http.get('/minecraft/endpoints'),
  verifyAccessKey: (accessKey) => http.post('/authorize/access-key', { access_key: accessKey }),
  session: () => http.get('/minecraft/session'),
  captureSauth: (payload = {}) => http.post('/minecraft/capture', payload),
  loginMinecraft: (sauth) => http.post('/minecraft/login', { sauth_json: sauth }),
  friends: () => http.get('/minecraft/friends'),
  friendDetails: () => http.get('/minecraft/friends/detail'),
  search: (params) => http.get('/minecraft/friends/search', { params }),
  addFriend: (payload) => http.post('/minecraft/friends/add', payload),
  removeFriend: (targetId) => http.delete(`/minecraft/friends/${encodeURIComponent(targetId)}`),
  profile: () => http.get('/minecraft/profile'),
  friendGroups: () => http.get('/minecraft/friends/groups'),
  friendGroupRelations: () => http.get('/minecraft/friends/groups/relations'),
  addFriendGroup: (payload) => http.post('/minecraft/friends/groups', payload),
  editFriendGroup: (groupId, payload) =>
    http.patch(`/minecraft/friends/groups/${encodeURIComponent(groupId)}`, payload),
  deleteFriendGroup: (groupId) =>
    http.delete(`/minecraft/friends/groups/${encodeURIComponent(groupId)}`),
  friendRequests: () => http.get('/minecraft/friends/requests'),
  replyFriendRequest: (targetId, agree) =>
    http.post(`/minecraft/friends/requests/${encodeURIComponent(targetId)}/reply`, { agree }),
  markFriend: (targetId, mark) =>
    http.post(`/minecraft/friends/${encodeURIComponent(targetId)}/mark`, { target_id: targetId, mark }),
  onlineStatus: (payload) => http.post('/minecraft/friends/online-status', payload),
  currentRoom: () => http.get('/minecraft/rooms/current'),
  friendsPlayingRooms: () => http.get('/minecraft/rooms/friends-playing'),
  recommendedRooms: () => http.get('/minecraft/rooms/recommended'),
  personalizedRooms: () => http.get('/minecraft/rooms/recommended/personalized'),
  roomSloganConfig: () => http.get('/minecraft/rooms/slogan-config'),
  searchRooms: (params) => http.get('/minecraft/rooms/search', { params }),
  roomWaterfall: (payload) => http.post('/minecraft/rooms/waterfall', payload),
  roomRecentResources: (payload) => http.post('/minecraft/rooms/recent-resources', payload),
  roomResIds: (payload) => http.post('/minecraft/rooms/res-ids', payload),
  roomsByRes: (payload) => http.post('/minecraft/rooms/by-res', payload),
  roomMultiInfo: (payload) => http.post('/minecraft/rooms/multi-info', payload),
  room: (roomId) => http.get(`/minecraft/rooms/${encodeURIComponent(roomId)}`),
  roomMembers: (roomId) => http.get(`/minecraft/rooms/${encodeURIComponent(roomId)}/members`),
  roomChatGroup: (roomId) => http.get(`/minecraft/rooms/${encodeURIComponent(roomId)}/chat-group`),
  createRoom: (payload) => http.post('/minecraft/rooms', payload),
  updateRoom: (roomId, payload) =>
    http.patch(`/minecraft/rooms/${encodeURIComponent(roomId)}`, payload),
  enterRoom: (roomId, payload = {}) =>
    http.post(`/minecraft/rooms/${encodeURIComponent(roomId)}/enter`, payload),
  leaveRoom: (roomId, payload = {}) =>
    http.post(`/minecraft/rooms/${encodeURIComponent(roomId)}/leave`, payload),
  kickRoomMember: (roomId, payload) =>
    http.post(`/minecraft/rooms/${encodeURIComponent(roomId)}/kick`, payload),
  matchRoom: (roomId, payload = {}) =>
    http.post(`/minecraft/rooms/${encodeURIComponent(roomId)}/match`, payload),
  lobbyCollections: () => http.get('/minecraft/lobby/collections'),
  lobbyBackups: () => http.get('/minecraft/lobby/backups'),
  lobbyRank: () => http.get('/minecraft/lobby/rank'),
  competitiveItem: () => http.get('/minecraft/lobby/competitive-item'),
  upstream: (path, payload = {}) => http.post('/minecraft/upstream', { path, payload }),
}
