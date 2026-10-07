<template>
  <figure class="chart">
    <figcaption>{{ chart.title }}</figcaption>
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="summary">
      <line :x1="padL" :x2="W - padR" :y1="zeroY" :y2="zeroY" class="axis" />
      <g v-for="(b, i) in bars" :key="i">
        <rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="4" :class="['bar', { neg: b.neg, last: i === bars.length - 1 }]" />
        <text :x="b.x + b.w / 2" :y="b.neg ? b.y + b.h + 15 : b.y - 7" text-anchor="middle" class="val">{{ chart.valueLabels[i] }}</text>
        <text :x="b.x + b.w / 2" :y="H - 12" text-anchor="middle" class="lab">{{ short(chart.labels[i]) }}</text>
      </g>
    </svg>
  </figure>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ chart: { type: Object, required: true } })
const W = 560, H = 270, padL = 20, padR = 20, padT = 30, padB = 34

const lo = computed(() => Math.min(0, ...props.chart.values))
const hi = computed(() => Math.max(0, ...props.chart.values))
const span = computed(() => (hi.value - lo.value) || 1)
const y = (v) => padT + ((hi.value - v) / span.value) * (H - padT - padB)
const zeroY = computed(() => y(0))

const bars = computed(() => {
  const n = props.chart.values.length
  const slot = (W - padL - padR) / n
  const w = Math.min(72, slot * 0.58)
  return props.chart.values.map((v, i) => {
    const top = y(Math.max(v, 0)), bottom = y(Math.min(v, 0))
    return { x: padL + slot * i + (slot - w) / 2, y: top, w, h: Math.max(2, bottom - top), neg: v < 0 }
  })
})
const short = (s) => (s.length > 11 ? s.slice(0, 10) + '…' : s)
const summary = computed(() => `${props.chart.title}: ` + props.chart.labels.map((l, i) => `${l} ${props.chart.valueLabels[i]}`).join(', '))
</script>

<style scoped>
.chart { margin: 10px 0; padding: 12px 14px 6px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; max-width: 600px; }
figcaption { font-weight: 600; font-size: 14px; margin-bottom: 2px; }
svg { width: 100%; height: auto; display: block; }
.axis { stroke: var(--line); stroke-width: 1; }
.bar { fill: color-mix(in srgb, var(--accent) 55%, var(--surface)); }
.bar.last { fill: var(--accent); }
.bar.neg { fill: var(--neg); }
.val { font-size: 13px; font-weight: 600; fill: var(--ink); }
.lab { font-size: 12px; fill: var(--muted); }
</style>
