<template>
  <div
    class="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-gray-900/70 backdrop-blur-sm"
    role="status"
    aria-live="polite"
    aria-label="Extraction in progress"
  >
    <div class="mx-4 w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-xl">

      <!-- Header -->
      <div class="mb-5 flex items-center gap-3">
        <div
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-100"
          aria-hidden="true"
        >
          <svg
            class="h-5 w-5 text-primary-600"
            :class="hasActiveStep ? 'animate-spin' : ''"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
        <div class="min-w-0">
          <h3 class="text-lg font-semibold text-secondary-800">
            Extracting metadata
          </h3>
          <p class="truncate text-sm text-gray-500">
            {{ activeStep ? activeStep.label : steps.length === 0 ? 'Starting…' : 'Finishing up…' }}
          </p>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="mb-3">
        <div class="mb-1.5 flex items-center justify-between text-xs text-gray-500">
          <span>
            {{ completedCount }} of {{ totalCount }} steps completed
          </span>
          <span class="font-medium text-primary-600">{{ progressPercent }}%</span>
        </div>

        <div class="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
          <!-- Indeterminate animation when nothing has started yet -->
          <div
            v-if="steps.length === 0"
            class="h-full w-1/3 animate-[indeterminate_1.4s_ease-in-out_infinite] rounded-full bg-primary-400"
          />
          <div
            v-else
            class="h-full rounded-full bg-primary-500 transition-all duration-500 ease-out"
            :style="{ width: `${progressPercent}%` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ExtractionProgress as Progress } from '../../composables/useApi'
import { computed, onMounted, onUnmounted, Ref, ref, watch } from 'vue'

const props = defineProps<{
  progressQueue: Progress[] | null
}>()

const stepMap = ref<Map<string, Progress>>(new Map())
const pipelineSize = ref<number | null>(null)

onMounted(() => {
  stepMap.value = new Map()
})

onUnmounted(() => {
  stepMap.value.clear()
})

const activeStep : Ref<Progress | null> = ref(null);

watch(
  () => props.progressQueue,
  (queue) => {
    if (!queue || !queue.length) return
    for (const p of queue) {
      activeStep.value = p
      if (p.pipeline_size) {
        pipelineSize.value = p.pipeline_size
      } else {
        stepMap.value.set(p.step, p)
      }
    }
    stepMap.value = new Map(stepMap.value)
  },
  { deep: true }
)

const steps = computed<Progress[]>(() => Array.from(stepMap.value.values()))

const totalCount = computed(() => pipelineSize.value ?? steps.value.length)

const completedCount = computed(
  () => steps.value.filter((s) => s.status === 'completed').length
)

const progressPercent = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((completedCount.value / totalCount.value) * 100)
})

const hasActiveStep = computed(() => activeStep.value !== null)

const activeStepIndex = computed(() => {
  if (!activeStep.value) return -1
  return steps.value.findIndex((s) => s.step === activeStep.value!.step)
})
</script>

<style scoped>
@keyframes indeterminate {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
</style>
