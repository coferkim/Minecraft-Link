<script setup>
import { ref } from 'vue'
import { AlertCircle, ArrowRight, Eye, EyeOff, KeyRound, LoaderCircle, ShieldCheck } from '@lucide/vue'
import { api, getErrorMessage } from '../api'
import BrandMark from './BrandMark.vue'

const emit = defineEmits(['authorized'])
const accessKey = ref('')
const visible = ref(false)
const loading = ref(false)
const error = ref('')
async function submit() {
  if (!accessKey.value.trim() || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.verifyAccessKey(accessKey.value.trim())
    localStorage.setItem('access_token', data.access_token)
    emit('authorized', data)
  } catch (err) { error.value = getErrorMessage(err, '访问密钥验证失败') }
  finally { loading.value = false }
}
</script>

<template>
  <main class="auth-page">
    <header class="auth-topbar"><BrandMark /><span><ShieldCheck :size="15" />本地安全会话</span></header>
    <div class="auth-content"><section class="auth-form-wrap">
      <div class="auth-steps" aria-label="登录步骤"><span class="active"><i>1</i>验证密钥</span><span class="step-connector"></span><span><i>2</i>连接账号</span></div>
      <div class="auth-heading"><KeyRound :size="28" :stroke-width="1.5" /><h1>回到你的方块世界</h1><p>验证访问密钥，连接好友与下一场冒险。</p></div>
      <form @submit.prevent="submit"><label class="field-label" for="access-key">访问密钥</label><div class="search-field auth-key-field" :class="{ invalid: error }"><KeyRound :size="17" /><input id="access-key" v-model="accessKey" :type="visible ? 'text' : 'password'" placeholder="输入访问密钥" autocomplete="current-password" :aria-invalid="Boolean(error)" :aria-describedby="error ? 'key-error' : undefined" autofocus /><button class="icon-button" type="button" :aria-label="visible ? '隐藏密钥' : '显示密钥'" :title="visible ? '隐藏密钥' : '显示密钥'" @click="visible = !visible"><EyeOff v-if="visible" :size="17" /><Eye v-else :size="17" /></button></div><p v-if="error" id="key-error" class="form-error" role="alert"><AlertCircle :size="15" />{{ error }}</p><button class="button primary wide auth-submit" type="submit" :disabled="!accessKey.trim() || loading"><LoaderCircle v-if="loading" class="spin" :size="17" />{{ loading ? '正在验证' : '验证并继续' }}<ArrowRight v-if="!loading" :size="17" /></button></form>
      <p class="auth-hint"><ShieldCheck :size="15" />使用服务端配置的访问密钥登录。</p>
    </section></div>
    <footer class="auth-footer"><span>Minecraft Link</span><span>属于你的连接，从这里开始。</span></footer>
  </main>
</template>
