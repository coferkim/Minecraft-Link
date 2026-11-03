<script setup>
import { onMounted, ref } from 'vue'
import { ArrowRight, ArrowUpRight, Blocks, BookOpen, DoorOpen, Gamepad2, HeartHandshake, Search, ShieldCheck, Users } from '@lucide/vue'

const emit = defineEmits(['navigate'])
const entered = ref(false)

onMounted(() => { entered.value = true })
</script>

<template>
  <section class="about-view" :class="{ 'about-entered': entered }">
    <div class="about-hero">
      <img class="about-project-icon" src="/minecraft-link.svg" alt="Minecraft Link 项目图标" width="160" height="160" />
      <div class="about-intro">
        <div class="about-kicker"><Blocks :size="15" /> MINECRAFT LINK <span>·</span> ABOUT</div>
        <h2>Minecraft-Link</h2>
        <p class="about-role">Minecraft 客户端接口桥接器</p>
        <p class="about-description">为网易版 Minecraft 基岩版提供轻量的本地接口入口。连接已经登录的游戏账号，查看好友、玩家资料与联机房间。</p>
        <div class="about-actions">
          <a class="button primary" href="https://github.com/coferkim/Minecraft-Link" target="_blank" rel="noopener noreferrer">查看 GitHub<ArrowUpRight :size="16" aria-hidden="true" /></a>
          <button class="button secondary" type="button" @click="emit('navigate', 'docs')"><BookOpen :size="16" />浏览 API 文档</button>
        </div>
      </div>
      <div class="about-edition"><span class="edition-mark"><Gamepad2 :size="17" /></span><span><strong>网易版</strong><small>基岩版客户端</small></span></div>
    </div>

    <div class="about-content-grid">
      <section class="about-section about-capabilities">
        <div class="about-section-heading"><span class="about-index">01</span><div><h3>为开放而生</h3><p>把客户端信息开放为人人都能调用的接口。</p></div></div>
        <div class="capability-list">
          <button type="button" class="capability-row" @click="emit('navigate', 'friends')"><span class="capability-icon"><Users :size="19" /></span><span><strong>好友与玩家</strong><small>查看在线状态、玩家资料和公开游戏动态。</small></span><ArrowRight :size="16" /></button>
          <button type="button" class="capability-row" @click="emit('navigate', 'rooms')"><span class="capability-icon"><DoorOpen :size="19" /></span><span><strong>联机房间</strong><small>查找房间，查看房主与房间成员资料。</small></span><ArrowRight :size="16" /></button>
          <button type="button" class="capability-row" @click="emit('navigate', 'docs')"><span class="capability-icon"><Search :size="19" /></span><span><strong>接口目录</strong><small>按分类检索参数、响应和请求示例。</small></span><ArrowRight :size="16" /></button>
        </div>
      </section>

      <section class="about-section about-connection">
        <div class="about-section-heading"><span class="about-index">02</span><div><h3>本地建立连接</h3><p>账号凭据留在本机登录流程中。</p></div></div>
        <ol class="connection-steps">
          <li><span class="step-number">1</span><div><strong>验证访问密钥</strong><small>进入本地服务工作台。</small></div><ShieldCheck :size="16" /></li>
          <li><span class="step-number">2</span><div><strong>连接已登录账号</strong><small>从本机启动器读取或手动提交 sauth。</small></div><Gamepad2 :size="16" /></li>
          <li><span class="step-number">3</span><div><strong>调用客户端接口</strong><small>查询好友、玩家资料和联机房间。</small></div><Blocks :size="16" /></li>
        </ol>
        <div class="about-local-note"><HeartHandshake :size="17" /><p>面向个人本地使用，不会要求你在此输入网易账号密码。</p></div>
      </section>
    </div>

    <footer class="about-signoff"><span><span class="signoff-dot"></span> 为方块世界里的每次相遇搭一座桥</span><strong>FerKim <span>×</span> Minecraft</strong></footer>
  </section>
</template>
