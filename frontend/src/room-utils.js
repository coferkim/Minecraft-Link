import { findCollection, normalizeRoomMember } from './api'

export function ensureUpstreamOk(payload) {
  const code = Number(payload?.code ?? payload?.statusCode ?? 0)
  if (code && code !== 200) throw new Error(payload?.message || payload?.msg || `上游返回状态码 ${code}`)
}

export function roomEntity(payload) {
  return payload?.entity || payload?.list?.[0] || payload?.data?.entity || payload?.data || null
}

export function roomMembers(payload, room, friendIds = []) {
  const candidates = [payload?.entity?.members, payload?.entity?.players, payload?.entity?.list, payload?.data?.members, payload?.data?.players, payload?.members]
  const rows = candidates.find(Array.isArray) || findCollection(payload)
  const order = room?.raw?.members
  const positions = Array.isArray(order) ? new Map(order.map((member, index) => [String(typeof member === 'object' ? member.uid ?? member.id : member), index])) : new Map()
  const friendSet = new Set(friendIds.map(String))
  const ownerId = room?.ownerId || payload?.entity?.hid || ''
  const ordered = positions.size ? [...rows].sort((a, b) => (positions.get(String(a?.uid ?? a?.id ?? a)) ?? Infinity) - (positions.get(String(b?.uid ?? b?.id ?? b)) ?? Infinity)) : rows
  return ordered.map((value, index) => {
    const source = typeof value === 'object' ? value : { uid: value }
    const member = normalizeRoomMember(source, index, ownerId)
    return { ...member, isFriend: member.isFriend || friendSet.has(member.id) }
  })
}
