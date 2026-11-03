<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import AccessGate from './components/AccessGate.vue'
import SocialConsole from './components/SocialConsole.vue'
import AccountLogin from './components/AccountLogin.vue'

const stage = ref('loading')
const mcUserId = ref(localStorage.getItem('mc_user_id') || '')

function moveToLogin() {
  stage.value = 'login'
}

function backToKey() {
  localStorage.removeItem('access_token')
  stage.value = 'key'
}

function enterConsole(result) {
  mcUserId.value = String(result?.user_id || localStorage.getItem('mc_user_id') || '')
  stage.value = 'panel'
}

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('mc_user_id')
  mcUserId.value = ''
  stage.value = 'key'
}

function handleExpired() {
  logout()
}

onMounted(() => {
  window.addEventListener('mc-session-expired', handleExpired)
  if (!localStorage.getItem('access_token')) {
    stage.value = 'key'
    return
  }
  if (!localStorage.getItem('mc_user_id')) {
    stage.value = 'login'
    return
  }
  mcUserId.value = localStorage.getItem('mc_user_id') || ''
  stage.value = 'panel'
})

onUnmounted(() => window.removeEventListener('mc-session-expired', handleExpired))
</script>

<template>
  <div class="app-root" v-if="stage !== 'loading'">
    <AccessGate v-if="stage === 'key'" @authorized="moveToLogin" />
    <AccountLogin
      v-else-if="stage === 'login'"
      @authenticated="enterConsole"
      @back="backToKey"
    />
    <SocialConsole v-else-if="stage === 'panel'" :mc-user-id="mcUserId" @logout="logout" />
  </div>
</template>
