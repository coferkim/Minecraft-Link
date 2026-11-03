<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({ open: Boolean, title: String, subtitle: String, drawer: Boolean, wide: Boolean, busy: Boolean })
const emit = defineEmits(['close'])
const panel = ref(null)
let previousFocus = null
let previousOverflow = ''
function close() { if (!props.busy) emit('close') }
function onKey(event) {
  if (!props.open) return
  if (event.key === 'Escape') { event.preventDefault(); close() }
  if (event.key !== 'Tab') return
  const nodes = [...(panel.value?.querySelectorAll('button:not(:disabled), input, textarea, select, a[href], summary, [tabindex="0"]') || [])].filter(node => node.getClientRects().length)
  const first = nodes[0]
  const last = nodes.at(-1)
  if (!first) { event.preventDefault(); return }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
function release() {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = previousOverflow
  if (previousFocus?.isConnected) previousFocus.focus()
}
watch(() => props.open, async (open, wasOpen) => {
  if (open) {
    previousFocus = document.activeElement
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKey)
    await nextTick()
    if (props.open) panel.value?.focus()
  } else if (wasOpen) release()
}, { immediate: true })
onBeforeUnmount(() => { if (props.open) release() })
</script>

<template>
  <Teleport to="body">
    <Transition :name="drawer ? 'sheet' : 'dialog'">
      <div v-if="open" class="overlay" :class="{ 'drawer-overlay': drawer }" @click.self="close">
        <section ref="panel" class="dialog-panel" :class="{ 'drawer-panel': drawer, 'dialog-wide': wide }" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1">
          <header class="dialog-heading">
            <div><span v-if="subtitle" class="overline">{{ subtitle }}</span><h2>{{ title }}</h2></div>
            <button class="icon-button" type="button" title="关闭" aria-label="关闭" :disabled="busy" @click="close"><X :size="19" /></button>
          </header>
          <div class="dialog-body"><slot /></div>
          <footer v-if="$slots.footer" class="dialog-footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
