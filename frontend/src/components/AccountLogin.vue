<script setup>
import { computed, ref } from 'vue'
import { AlertCircle, ArrowLeft, ArrowRight, Check, Copy, Gamepad2, LoaderCircle, Monitor, ScanSearch, ShieldCheck } from '@lucide/vue'
import { api, getErrorMessage, unwrapSauth } from '../api'
import BrandMark from './BrandMark.vue'

const emit = defineEmits(['authenticated', 'back'])
const mode = ref('capture')
const text = ref('')
const parsed = ref(null)
const captured = ref(false)
const copied = ref(false)
const loading = ref(false)
const capturing = ref(false)
const error = ref('')
const canSubmit = computed(() => Boolean(parsed.value) && !loading.value && !capturing.value)
function parseInput() {
  error.value = ''
  parsed.value = null
  if (!text.value.trim()) return
  try { parsed.value = unwrapSauth(text.value) }
  catch (err) { error.value = err.message }
}
async function capture() {
  if (capturing.value || loading.value) return
  capturing.value = true
  error.value = ''
  try {
    const { data } = await api.captureSauth()
    text.value = JSON.stringify(data.sauth, null, 2)
    captured.value = true
    copied.value = false
    parseInput()
  } catch (err) { error.value = getErrorMessage(err, '读取失败，请确认发烧启动器或游戏已登录并正在运行。') }
  finally { capturing.value = false }
}
async function copySauth() {
  try {
    await navigator.clipboard.writeText(text.value)
    copied.value = true
    window.setTimeout(() => { copied.value = false }, 1800)
  } catch {
    error.value = '无法访问剪贴板，请手动复制下方 JSON。'
  }
}
async function submit() {
  parseInput()
  if (!canSubmit.value) return
  loading.value = true
  try {
    const { data } = await api.loginMinecraft(parsed.value)
    localStorage.setItem('mc_user_id', String(data.user_id))
    emit('authenticated', data)
  } catch (err) { error.value = getErrorMessage(err, 'Minecraft 登录失败') }
  finally { loading.value = false }
}
</script>

<template>
  <main class="auth-page account-login-page">
    <header class="auth-topbar"><BrandMark /><button class="text-link" type="button" :disabled="loading || capturing" @click="emit('back')"><ArrowLeft :size="15" />返回验证</button></header>
    <div class="auth-content account-login-content"><section class="auth-form-wrap account-login">
      <div class="auth-steps" aria-label="登录步骤"><span class="complete"><i><Check :size="12" /></i>验证密钥</span><span class="step-connector"></span><span class="active"><i>2</i>连接账号</span></div>
      <div class="auth-heading"><Gamepad2 :size="30" :stroke-width="1.5" /><h1>连接我的世界</h1><p>你的好友和联机世界，正在等你。</p></div>
      <div class="segmented auth-mode" role="group" aria-label="登录凭据来源"><button type="button" :class="{ active: mode === 'capture' }" :aria-pressed="mode === 'capture'" :disabled="capturing || loading" @click="mode = 'capture'"><Monitor :size="15" />本机读取</button><button type="button" :class="{ active: mode === 'manual' }" :aria-pressed="mode === 'manual'" :disabled="capturing || loading" @click="mode = 'manual'">手动输入</button></div>
      <div v-if="mode === 'capture'" class="capture-section"><Monitor :size="36" :stroke-width="1.2" /><h2>{{ parsed ? '已找到你的登录凭据' : '从本机连接账号' }}</h2><p>{{ parsed ? '凭据已就绪，继续登录即可进入控制台。' : '先打开已登录的发烧启动器或我的世界，然后读取登录凭据。' }}</p><button class="button secondary" type="button" :disabled="capturing || loading" @click="capture"><LoaderCircle v-if="capturing" class="spin" :size="16" /><ScanSearch v-else :size="16" />{{ capturing ? '正在读取' : parsed ? '重新读取' : '读取登录凭据' }}</button></div>
      <section v-if="mode === 'capture' && captured" class="captured-sauth" aria-label="读取到的 sauth JSON">
        <div class="captured-sauth-head"><strong>sauth JSON</strong><button class="button secondary compact" type="button" aria-label="复制 sauth JSON" @click="copySauth"><Check v-if="copied" :size="14" /><Copy v-else :size="14" />{{ copied ? '已复制' : '复制 JSON' }}</button></div>
        <pre id="captured-sauth-json">{{ text }}</pre>
        <p class="sauth-warning"><ShieldCheck :size="14" />包含账号会话凭据，请勿分享。</p>
      </section>
      <div v-else-if="mode === 'manual'" class="manual-section"><label class="field-label" for="sauth-input">sauth JSON</label><textarea id="sauth-input" v-model="text" class="text-area code-input" placeholder="粘贴 sauth 或 sauth_json 对象" spellcheck="false" @input="captured = false; parseInput()"></textarea><p class="field-help">支持完整 sauth 对象，或包含 sauth_json 的外层对象。</p></div>
      <p v-if="parsed" class="credential-ready" role="status"><Check :size="15" />登录凭据已通过格式校验</p>
      <p v-if="error" class="form-error" role="alert"><AlertCircle :size="16" />{{ error }}</p>
      <button class="button primary wide auth-submit" type="button" :disabled="!canSubmit" @click="submit"><LoaderCircle v-if="loading" :size="17" class="spin" />{{ loading ? '正在连接账号' : '登录并进入控制台' }}<ArrowRight v-if="!loading" :size="17" /></button>
      <p class="auth-hint"><ShieldCheck :size="15" />凭据通过本机服务交换，建立账号会话。</p>
    </section></div>
    <footer class="auth-footer"><span>Minecraft Link</span><span>属于你的连接，从这里开始。</span></footer>
  </main>
</template>
