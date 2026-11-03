<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { AlertCircle, ArrowRight, Braces, Check, ChevronRight, Code2, Copy, FileCode2, KeyRound, LoaderCircle, RefreshCw, Search } from '@lucide/vue'
import { api, getErrorMessage, http } from '../api'

const loading = ref(false)
const error = ref('')
const schemaError = ref('')
const catalog = ref([])
const spec = ref(null)
const query = ref('')
const group = ref('all')
const selectedKey = ref('GET /minecraft/friends')
const copied = ref(false)
const responseStatus = ref('200')
const groups = { auth: '登录认证', authorize: '访问认证', profile: '账号资料', friends: '好友与玩家', rooms: '联机房间', lobby: '大厅', upstream: '上游调用', system: '服务状态', other: '其他接口' }

const operations = computed(() => {
  const known = new Map(catalog.value.map(item => [`${item.method.toUpperCase()} ${item.path}`, item]))
  for (const [path, methods] of Object.entries(spec.value?.paths || {})) {
    for (const [method, operation] of Object.entries(methods)) {
      if (!['get', 'post', 'patch', 'put', 'delete'].includes(method)) continue
      const key = `${method.toUpperCase()} ${path}`
      const previous = known.get(key)
      const category = path.startsWith('/authorize') ? 'authorize' : path.startsWith('/minecraft') ? path.split('/')[2] : 'system'
      known.set(key, { ...previous, path, method: method.toUpperCase(), description: previous?.description || operation.summary || path, group: previous?.group || (groups[category] ? category : 'other'), operation })
    }
  }
  return [...known.values()].map(item => ({ ...item, key: `${item.method} ${item.path}` }))
})
const categories = computed(() => [...new Set(operations.value.map(item => item.group))].map(id => ({ id, name: groups[id] || id, count: operations.value.filter(item => item.group === id).length })))
const filtered = computed(() => operations.value.filter(item => (group.value === 'all' || item.group === group.value) && [item.path, item.method, item.description, groups[item.group]].some(value => String(value || '').toLowerCase().includes(query.value.trim().toLowerCase()))))
const selected = computed(() => filtered.value.find(item => item.key === selectedKey.value) || filtered.value[0] || null)
function resolve(schema) {
  if (!schema) return {}
  if (schema.$ref) return spec.value?.components?.schemas?.[schema.$ref.split('/').at(-1)] || {}
  return schema
}
function typeOf(schema) {
  const value = resolve(schema)
  if (value.anyOf) return value.anyOf.map(typeOf).join(' | ')
  if (value.type === 'array') return `${typeOf(value.items)}[]`
  return value.type || (value.properties ? 'object' : 'any')
}
function example(schema, depth = 0) {
  const value = resolve(schema)
  if (depth > 4) return {}
  if (value.example !== undefined) return value.example
  if (value.default !== undefined && value.default !== null) return value.default
  if (value.enum) return value.enum[0]
  if (value.anyOf) return example(value.anyOf.find(s => s.type !== 'null') || value.anyOf[0], depth + 1)
  if (value.properties) return Object.fromEntries(Object.entries(value.properties).map(([key, field]) => [key, example(field, depth + 1)]))
  if (value.type === 'array') return [example(value.items, depth + 1)]
  if (value.type === 'boolean') return false
  if (['integer', 'number'].includes(value.type)) return 0
  if (value.type === 'object') return {}
  return 'string'
}
const requestSchema = computed(() => resolve(selected.value?.operation?.requestBody?.content?.['application/json']?.schema))
const fields = computed(() => [
  ...(selected.value?.operation?.parameters || []).map(field => ({ ...field, schema: resolve(field.schema) })),
  ...Object.entries(requestSchema.value?.properties || {}).map(([name, schema]) => ({ name, schema: resolve(schema), required: requestSchema.value.required?.includes(name), in: 'body', description: resolve(schema).description })),
])
const bodyExample = computed(() => selected.value?.operation?.requestBody ? JSON.stringify(example(requestSchema.value), null, 2) : '')
const responses = computed(() => Object.entries(selected.value?.operation?.responses || {}))
const response = computed(() => selected.value?.operation?.responses?.[responseStatus.value] || responses.value[0]?.[1])
watch(() => selected.value?.key, () => { responseStatus.value = responses.value.some(([status]) => status === '200') ? '200' : responses.value[0]?.[0] || '200' })
const responseExample = computed(() => {
  const content = response.value?.content?.['application/json']
  if (content?.example) return JSON.stringify(content.example, null, 2)
  const schema = resolve(content?.schema)
  return Object.keys(schema).length ? JSON.stringify(example(schema), null, 2) : ''
})
const curl = computed(() => {
  if (!selected.value) return ''
  let path = selected.value.path
  const params = selected.value.operation?.parameters || []
  params.filter(p => p.in === 'path').forEach(p => { path = path.replace(`{${p.name}}`, p.name.includes('id') ? '123456' : 'value') })
  const qs = params.filter(p => p.in === 'query' && p.required).map(p => `${p.name}=${encodeURIComponent(example(p.schema))}`).join('&')
  if (qs) path += `?${qs}`
  const lines = [`curl -X ${selected.value.method} '${location.origin}/api${path}'`]
  if (selected.value.path.startsWith('/minecraft')) lines.push("  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'")
  if (bodyExample.value) { lines.push("  -H 'Content-Type: application/json'"); lines.push(`  -d '${bodyExample.value.replaceAll("'", "'\\''")}'`) }
  return lines.join(' \\\n')
})
async function load() {
  loading.value = true
  error.value = ''
  schemaError.value = ''
  const responses = await Promise.allSettled([api.endpoints(), http.get('/openapi.json')])
  if (responses[0].status === 'fulfilled') catalog.value = responses[0].value.data?.local_endpoints || []
  else error.value = getErrorMessage(responses[0].reason, '接口目录加载失败')
  if (responses[1].status === 'fulfilled') spec.value = responses[1].value.data
  else schemaError.value = getErrorMessage(responses[1].reason, '参数定义加载失败')
  loading.value = false
}
async function copy() {
  try { await navigator.clipboard.writeText(curl.value); copied.value = true; setTimeout(() => { copied.value = false }, 1800) }
  catch { schemaError.value = '复制失败，请在请求示例中手动选择内容' }
}
onMounted(load)
</script>

<template>
  <section class="api-docs-view">
    <div class="docs-summary"><div><KeyRound :size="18" /><span>请求认证 <code>Authorization: Bearer &lt;token&gt;</code></span></div><span>{{ operations.length }} 个接口</span><button class="icon-button" type="button" title="刷新文档" aria-label="刷新文档" :disabled="loading" @click="load"><RefreshCw :size="16" :class="{ spin: loading }" /></button></div>
    <div v-if="error || schemaError" class="notice" role="alert"><AlertCircle :size="17" /><span>{{ error || schemaError }}</span><button type="button" @click="load">重试</button></div>
    <div class="docs-layout">
      <aside class="docs-index"><label class="search-field"><Search :size="15" /><input v-model="query" placeholder="搜索接口" aria-label="搜索接口" /></label><label class="docs-group-select"><span>接口分类</span><select v-model="group"><option value="all">全部接口</option><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }} · {{ category.count }}</option></select></label><div v-if="loading && !operations.length" class="inline-empty"><LoaderCircle :size="17" class="spin" />正在读取接口</div><div v-else class="endpoint-index"><button v-for="item in filtered" :key="item.key" type="button" :class="{ active: selected?.key === item.key }" @click="selectedKey = item.key; responseStatus = '200'"><span class="method-label" :class="item.method.toLowerCase()">{{ item.method }}</span><span><strong>{{ item.description }}</strong><code>{{ item.path }}</code></span></button><p v-if="!filtered.length" class="inline-empty">没有匹配的接口。</p></div></aside>
      <article v-if="selected" class="endpoint-detail"><div class="endpoint-category"><FileCode2 :size="14" />{{ groups[selected.group] || selected.group }}<ChevronRight :size="12" />{{ selected.method }}</div><h2>{{ selected.description }}</h2><div class="endpoint-url"><span class="method-label" :class="selected.method.toLowerCase()">{{ selected.method }}</span><code>/api{{ selected.path }}</code></div><p v-if="selected.operation?.description" class="endpoint-intro">{{ selected.operation.description }}</p>
        <section class="doc-section"><h3>请求参数<span>{{ fields.length }}</span></h3><div v-if="fields.length" class="parameter-list"><div class="parameter-table-head"><span>名称 / 类型</span><span>位置</span><span>说明</span></div><div v-for="field in fields" :key="`${field.in}-${field.name}`" class="parameter-row"><div><code>{{ field.name }}</code><small>{{ typeOf(field.schema) }} <em v-if="field.required">必填</em></small></div><span class="parameter-location">{{ field.in }}</span><p>{{ field.description || field.schema.title || '—' }}<small v-if="field.schema.default !== undefined">默认值：{{ JSON.stringify(field.schema.default) }}</small></p></div></div><p v-else class="muted">{{ selected.operation ? selected.operation.requestBody ? '接收 JSON 对象，请参考请求示例。' : '此接口无需额外参数。' : '该接口暂未提供参数定义。' }}</p></section>
        <section class="doc-section"><div class="section-heading"><h3><Code2 :size="16" />请求示例</h3><button class="text-link" type="button" @click="copy"><Check v-if="copied" :size="14" /><Copy v-else :size="14" />{{ copied ? '已复制' : '复制 cURL' }}</button></div><pre class="code-block">{{ curl }}</pre></section>
        <section class="doc-section"><div class="section-heading"><h3><Braces :size="16" />响应</h3><select v-if="responses.length" v-model="responseStatus" class="response-select" aria-label="响应状态"><option v-for="[status] in responses" :key="status" :value="status">{{ status }}</option></select></div><p class="muted response-description">{{ response?.description || '返回上游接口的 JSON 数据。' }}</p><pre v-if="responseExample" class="code-block">{{ responseExample }}</pre><div v-else class="inline-empty">返回结构由上游数据决定。</div></section>
      </article>
      <div v-else class="empty-state docs-empty"><FileCode2 :size="30" :stroke-width="1.4" /><h2>{{ loading ? '正在准备接口文档' : '没有匹配的接口' }}</h2><p>选择分类或搜索路径，查看接口详情。</p></div>
    </div>
  </section>
</template>
