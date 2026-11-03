// Synthetic accounts and intercepted responses. No launcher or upstream account is accessed.
const image = source => `data:image/svg+xml,${encodeURIComponent(source)}`
const avatar = (skin, eyes) => image(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><path fill="${skin}" d="M0 0h64v64H0z"/><path fill="#342b28" d="M0 0h64v18H0zM0 12h12v18H0zM52 12h12v18H52z"/><path fill="#f4f2e8" d="M10 29h17v10H10zM38 29h17v10H38z"/><path fill="${eyes}" d="M19 29h8v10h-8zM38 29h8v10h-8z"/><path fill="#6c4540" d="M21 48h24v7H21z"/></svg>`)
export const frame = image('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="none" stroke="#dfba69" stroke-width="4"/><path fill="#dfba69" d="m45 5 5-5 5 5-5 5zM5 45l5 5-5 5-5-5zm90 0 5 5-5 5-5-5zM45 95l5-5 5 5-5 5z"/></svg>')
export const room = { rid: 563105, name: '周末生存 · 一起建个家', hid: 10002, cnt: 4, cap: 10, members: [10002, 10001, 10006, 10008], map_name: '原版生存' }
export const friends = [
  { id: 10004, nickname: '山间晚风', online_status: false },
  { id: 10001, nickname: '方块旅人', online_status: true, game_info: { 'game-info': JSON.stringify({ room_id: room.rid, room_name: room.name }) } },
  { id: 10002, nickname: '小森同学', online_status: true, game_info: { 'game-info': JSON.stringify({ room_id: room.rid, room_name: room.name }) } },
  { id: 10003, nickname: '不吃香菜', online_status: true },
  { id: 10005, nickname: '像素与远方', online_status: false },
  { id: 10006, nickname: '橡木工作台' },
  { id: 10007, nickname: '夜航的星星', online: 'false' },
].map((player, index) => ({ ...player, headImage: avatar(['#b89574', '#aa8b6b', '#dabaa0', '#7996a1', '#c5977e', '#bbaa91', '#738e77'][index], '#476274'), frame_id: index === 1 || index === 2 ? frame : '', pe_growth: { lv: 12 + index * 7 }, signature: '一起探索新的世界。' }))
export const sauth = { client_login_sn: 'test-login', udid: 'test-udid', deviceid: 'test-device', sdkuid: 'test-sdk', sessionid: 'test-session' }
const endpoint = (method, path, description, group) => ({ method, path, description, group })
export const catalog = [
  endpoint('GET', '/minecraft/friends', '获取好友列表', 'friends'),
  endpoint('GET', '/minecraft/friends/search', '搜索玩家', 'friends'),
  endpoint('POST', '/minecraft/friends/add', '发送好友请求', 'friends'),
  endpoint('GET', '/minecraft/rooms/{room_id}', '查询房间详细信息', 'rooms'),
]
export const openapi = {
  openapi: '3.1.0',
  paths: {
    '/minecraft/friends': { get: { responses: { 200: { description: '好友列表' } } } },
    '/minecraft/friends/search': { get: { parameters: [{ name: 'name', in: 'query', required: false, schema: { type: 'string' }, description: '玩家昵称或邮箱' }], responses: { 200: { description: '玩家列表' } } } },
    '/minecraft/friends/add': { post: { requestBody: { content: { 'application/json': { schema: { $ref: '#/components/schemas/FriendActionRequest' } } } }, responses: { 200: { description: '操作结果' } } } },
    '/minecraft/rooms/{room_id}': { get: { parameters: [{ name: 'room_id', in: 'path', required: true, schema: { type: 'string' }, description: '房间号' }], responses: { 200: { description: '房间资料' }, 422: { description: '参数验证失败' } } } },
  },
  components: { schemas: { FriendActionRequest: { type: 'object', required: ['target_id'], properties: { target_id: { type: 'string', description: '目标玩家 UID' }, message: { type: 'string', default: '', description: '验证消息' } } } } },
}

export async function mockApi(page, options = {}) {
  const calls = []
  const marks = new Map()
  const approved = []
  let applications = options.emptyRequests ? [] : [
    { fid: 10008, nickname: '远行的冒险家', headImage: friends[0].headImage, frame_id: frame, verify_msg: '一起探索新的世界' },
    { user: { id: 10009, nickname: '桦林向导', headImage: friends[3].headImage }, message: '周末一起建造吗？' },
  ]
  await page.route('**/api/**', async route => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace(/^\/api/, '')
    calls.push({ path, method: request.method(), query: Object.fromEntries(url.searchParams), body: request.postData() ? request.postDataJSON() : null })
    let body = { code: 0, list: [] }
    let status = 200
    if (path === '/authorize/access-key') {
      if (request.postDataJSON().access_key === 'wrong-key') { body = { detail: '访问密钥不正确' }; status = 401 }
      else body = { access_token: 'synthetic-ui-token' }
    } else if (path === '/minecraft/capture') body = { sauth, process_name: 'test-process', pid: 1 }
    else if (path === '/minecraft/login') body = { user_id: 900000 }
    else if (path === '/minecraft/friends' || path === '/minecraft/friends/detail') {
      if (options.failFriends) { body = { detail: '暂时无法读取好友' }; status = 503 }
      else body = { code: 0, entities: options.empty ? [] : [...friends, ...approved].map(player => ({ ...player, ...(marks.has(String(player.id)) ? { mark: marks.get(String(player.id)) } : {}) })) }
    } else if (path === '/minecraft/friends/requests') {
      if (options.failRequests) { body = { detail: '暂时无法读取好友申请' }; status = 503 }
      else body = { code: 0, entities: applications }
    } else if (/^\/minecraft\/friends\/requests\/\d+\/reply$/.test(path)) {
      if (options.failReply) body = { code: 500, message: '好友申请处理失败' }
      else {
        const id = path.split('/')[4]
        const application = applications.find(item => String(item.fid || item.user?.id) === id)
        if (request.postDataJSON().agree && application) approved.push({ ...(application.user || application), id })
        applications = applications.filter(item => String(item.fid || item.user?.id) !== id)
      }
    } else if (/^\/minecraft\/friends\/\d+\/mark$/.test(path)) {
      if (options.failMark) { body = { detail: '备注保存失败' }; status = 503 }
      else marks.set(path.split('/')[3], request.postDataJSON().mark)
    } else if (path === '/minecraft/profile') {
      if (options.failProfile) { body = { detail: '账号资料读取失败' }; status = 503 }
      else body = { code: 0, entity: { entity_id: 900000, name: options.profileName || '方块建筑师', avatar: 'legacy-avatar-id', head_image: friends[0].headImage, avatar_image_url: friends[0].headImage, frame_id: frame, level: 1, ...(options.profileLevelUnavailable ? {} : { pe_growth: { lv: 42 } }), signature: '把想象建成自己的世界。' }, ...(options.profileLevelUnavailable ? { profile_details_warning: '游戏资料暂未同步，账号等级暂不显示。' } : {}) }
    } else if (path === '/minecraft/session') body = { authenticated: true, user_id: '900000', updated_at: '2026-11-03T09:30:00+08:00' }
    else if (path === '/minecraft/friends/search') body = { code: 0, entities: url.searchParams.get('name') === 'missing-player' ? [] : [{ id: 10008, nickname: '远行的冒险家', online_status: true, headImage: avatar('#9d7760', '#444'), game_info: { 'game-info': JSON.stringify({ room_id: room.rid, room_name: room.name }) } }] }
    else if (path === '/minecraft/rooms/563105') {
      if (options.slowRooms) await new Promise(resolve => setTimeout(resolve, 450))
      body = { code: 0, entity: room, list: [room] }
    } else if (path === '/minecraft/rooms/563105/members') {
      if (options.slowRooms) await new Promise(resolve => setTimeout(resolve, 450))
      body = { code: 0, entity: { ...room, members: [10008, 10001, 10006, 10002].map(id => friends.find(player => player.id === id) || { id, nickname: '远行的冒险家', headImage: avatar('#9d7760', '#444') }) } }
    } else if (path === '/minecraft/rooms/current') {
      if (options.failCurrentRoom) { body = { detail: '当前房间读取失败' }; status = 503 }
      else body = { code: 0, entity: null }
    }
    else if (path.startsWith('/minecraft/rooms/') && /^\/minecraft\/rooms\/\d+$/.test(path)) body = { code: 0, list: [] }
    else if (path === '/minecraft/endpoints') body = { local_endpoints: catalog }
    else if (path === '/openapi.json') body = openapi
    await route.fulfill({ status, json: body })
  })
  return calls
}

export async function authorize(page) {
  await page.addInitScript(() => { localStorage.setItem('access_token', 'synthetic-ui-token'); localStorage.setItem('mc_user_id', '900000') })
}

export async function navigate(page, name) {
  const sidebar = page.locator('.sidebar')
  if (await sidebar.isVisible()) await sidebar.getByRole('button', { name, exact: true }).click()
  else { await page.getByRole('button', { name: '打开导航', exact: true }).click(); await page.locator('.mobile-nav').getByRole('button', { name, exact: true }).click() }
  await page.locator('.overlay').waitFor({ state: 'hidden' })
}

export async function settleMotion(page) {
  await page.evaluate(async () => {
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    await Promise.all(document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity).map(animation => animation.finished.catch(() => {})))
  })
}
