<template>
  <div class="min-h-full bg-gray-50 py-6 sm:py-8">
    <div class="container-custom w-full space-y-8">
      <Card padding="p-6 sm:p-8" custom-class="rounded-xl">
        <form class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5" @submit.prevent="onExtract">
          <!-- Row 1: Repository URL | Schema -->
          <div>
            <Input
              id="repo-url"
              v-model="repoUrl"
              type="url"
              required
              label="Repository URL"
              placeholder="https://github.com/owner/repo"
            />
          </div>

          <div>
            <label for="schema" class="label block text-sm font-medium text-secondary-800 mb-1.5">
              Schema
            </label>
            <select
              id="schema"
              v-model="schema"
              class="input-field w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-secondary-800 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="maSMP">maSMP</option>
              <option value="CodeMeta">CodeMeta</option>
            </select>
          </div>

          <!-- Row 2: Access token | Extract button -->
          <div class="relative">
            <label for="access-token" class="label block text-sm font-medium text-secondary-800 mb-1.5">
              Access token
              <button
                type="button"
                aria-label="How to get a GitHub or GitLab access token"
                class="inline-flex items-center justify-center w-4 h-4 ml-1 rounded-full border border-gray-300 bg-gray-50 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 align-middle"
                @click="showTokenTip = !showTokenTip"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
                </svg>
              </button>
            </label>
            <Input
              id="access-token"
              v-model="accessToken"
              type="password"
              placeholder="Optional for public repos"
            />

            <!-- Info tip popover -->
            <Teleport to="body">
              <div
                v-if="showTokenTip"
                class="fixed inset-0 z-40 bg-black/20"
                aria-hidden="true"
                @click="showTokenTip = false"
              />
              <div
                v-if="showTokenTip"
                class="fixed z-50 w-[calc(100vw-2rem)] max-w-sm top-1/2 -translate-y-1/2 left-4 right-4 sm:left-1/2 sm:right-auto sm:-translate-x-1/2 rounded-xl border border-gray-200 bg-white shadow-xl"
                role="dialog"
                aria-labelledby="token-tip-title"
                @click.stop
              >
                <div class="flex items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 bg-gray-50/80 rounded-t-xl">
                  <h3 id="token-tip-title" class="text-sm font-semibold text-secondary-800">
                    Access token
                  </h3>
                  <button
                    type="button"
                    aria-label="Close"
                    class="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    @click="showTokenTip = false"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <div class="p-4 max-h-[60vh] overflow-y-auto">
                  <p class="text-sm text-gray-600 mb-3 leading-relaxed">
                    Required for private repos; recommended for public repos to avoid API limits. Use a GitHub token for github.com URLs and a GitLab token for gitlab.com.
                  </p>
                  <!-- Tabs -->
                  <div class="flex border-b border-gray-200 mb-3">
                    <button
                      type="button"
                      :class="[
                        'px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                        tokenTipTab === 'github'
                          ? 'border-primary-500 text-primary-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      ]"
                      @click="tokenTipTab = 'github'"
                    >
                      GitHub
                    </button>
                    <button
                      type="button"
                      :class="[
                        'px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                        tokenTipTab === 'gitlab'
                          ? 'border-primary-500 text-primary-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      ]"
                      @click="tokenTipTab = 'gitlab'"
                    >
                      GitLab
                    </button>
                  </div>
                  <!-- GitHub -->
                  <div v-show="tokenTipTab === 'github'" class="space-y-2">
                    <p class="text-xs font-medium text-secondary-800 uppercase tracking-wide mb-2">
                      How to get one (GitHub)
                    </p>
                    <ol class="list-decimal list-inside text-sm text-gray-600 space-y-1.5 leading-relaxed">
                      <li>Go to <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:text-primary-700 underline underline-offset-1">GitHub Developer Settings</a></li>
                      <li>Click <strong class="text-gray-800">"Generate new token (classic)"</strong></li>
                      <li>Set <strong class="text-gray-800">expiration</strong> (optional)</li>
                      <li>Enable scopes: <strong class="text-gray-800">repo</strong> (private repos), <strong class="text-gray-800">read:org</strong> (org repos)</li>
                      <li>Click <strong class="text-gray-800">"Generate token"</strong></li>
                      <li>Copy and store it securely, it won’t be shown again.</li>
                    </ol>
                  </div>
                  <!-- GitLab -->
                  <div v-show="tokenTipTab === 'gitlab'" class="space-y-2">
                    <p class="text-xs font-medium text-secondary-800 uppercase tracking-wide mb-2">
                      How to get one (GitLab)
                    </p>
                    <ol class="list-decimal list-inside text-sm text-gray-600 space-y-1.5 leading-relaxed">
                      <li>Go to <a href="https://gitlab.com/-/user_settings/personal_access_tokens" target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:text-primary-700 underline underline-offset-1">GitLab Access Tokens</a> (or Profile → Edit profile → Access Tokens)</li>
                      <li>Click <strong class="text-gray-800">"Add new token"</strong></li>
                      <li>Give the token a name and set <strong class="text-gray-800">expiration</strong> (optional)</li>
                      <li>Enable scopes: <strong class="text-gray-800">read_api</strong> (public repos), <strong class="text-gray-800">read_repository</strong> (private repos)</li>
                      <li>Click <strong class="text-gray-800">"Create personal access token"</strong></li>
                      <li>Copy and store it securely, it won’t be shown again.</li>
                    </ol>
                  </div>
                </div>
              </div>
            </Teleport>
          </div>

          <!-- Row: Extract button (73.5%) + FAIRness checkbox (26.5%).
               On mobile: stack vertically (button then checkbox).
               On >=sm: show side-by-side with 73.5/26.5 split. -->
          <div class="flex flex-col sm:flex-row items-end gap-2">
            <div class="w-full sm:flex-[0_0_73.5%]">
              <Button
                type="submit"
                :disabled="isLoading"
                custom-class="w-full justify-center"
              >
                {{ isLoading ? 'Extracting…' : 'Extract' }}
              </Button>
            </div>

            <!-- <label
              for="run-fairness"
              class="inline-flex items-center justify-start gap-2 w-full sm:flex-[0_0_26.5%]"
            >
              <input
                id="run-fairness"
                v-model="runFairness"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span class="text-sm text-secondary-800">
                Assess FAIRness
              </span>
            </label> -->
          </div>

          <p v-if="error" class="text-sm text-red-600 sm:col-span-2">
            {{ error }}
          </p>
        </form>
      </Card>

      <!-- Results: loading overlay + result panel (teleport so overlay covers full page including header/footer) -->
      <Teleport to="body">
        <ExtractionProgress v-if="isLoading" :key="extractionKey" :progressQueue="progressQueue" />
      </Teleport>
      <Card
        v-if="extractionResult && !isLoading"
        padding="p-6 sm:p-8"
        custom-class="rounded-xl"
      >
        <div class="space-y-6">
          <div
            v-if="fairness || fairnessError"
            class="border-b border-gray-200"
          >
            <nav class="-mb-px flex gap-4" aria-label="Result views">
              <button
                v-for="tab in resultsTabs"
                :key="tab.key"
                type="button"
                :class="[
                  'border-b-2 px-1 py-2 text-sm font-medium transition-colors',
                  activeResultsTab === tab.key
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                ]"
                @click="activeResultsTab = tab.key"
              >
                {{ tab.label }}
              </button>
            </nav>
          </div>

          <div v-if="activeResultsTab === 'metadata' || !fairness">
            <MetadataResults :result="extractionResult" />
          </div>

          <div v-else class="space-y-6">
            <div class="space-y-1">
              <h2 class="text-lg sm:text-xl font-semibold text-secondary-800">
                FAIRness summary
              </h2>
              <p class="mt-1 text-sm text-gray-600">
                Overall FAIRness score and per-principle scores for the selected repository.
              </p>
              <p class="mt-1 text-xs text-gray-500">
                Based on FAIRness indicators derived from 10 FAIR best practices for research software
                (description, identifier, download URL, versioning, documentation, license, citation,
                metadata, installation, requirements).
              </p>
            </div>

            <div
              v-if="fairnessError"
              class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {{ fairnessError }}
            </div>

            <div v-if="fairness">
              <div class="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-4">
                <div class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
                  <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">
                    Overall
                  </p>
                  <p class="text-xl font-semibold text-primary-600">
                    {{ (fairness.overall_score * 100).toFixed(0) }}%
                  </p>
                </div>
                <div class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
                  <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">
                    Findable
                  </p>
                  <p class="text-xl font-semibold text-primary-600">
                    {{ (fairness.findable * 100).toFixed(0) }}%
                  </p>
                </div>
                <div class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
                  <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">
                    Accessible
                  </p>
                  <p class="text-xl font-semibold text-primary-600">
                    {{ (fairness.accessible * 100).toFixed(0) }}%
                  </p>
                </div>
                <div class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
                  <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">
                    Interoperable
                  </p>
                  <p class="text-xl font-semibold text-primary-600">
                    {{ (fairness.interoperable * 100).toFixed(0) }}%
                  </p>
                </div>
                <div class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
                  <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">
                    Reusable
                  </p>
                  <p class="text-xl font-semibold text-primary-600">
                    {{ (fairness.reusable * 100).toFixed(0) }}%
                  </p>
                </div>
              </div>

              <div v-if="groupedIndicators" class="space-y-6">
                <section v-if="groupedIndicators.documentation.length">
                  <h3 class="text-sm font-semibold text-secondary-800 mb-3">
                    Documentation &amp; governance
                  </h3>
                  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    <FairnessIndicatorDonut
                      v-for="indicator in groupedIndicators.documentation"
                      :key="indicator.id"
                      :indicator="indicator"
                    />
                  </div>
                </section>

                <section v-if="groupedIndicators.findability.length">
                  <h3 class="text-sm font-semibold text-secondary-800 mb-3">
                    Findability &amp; metadata
                  </h3>
                  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    <FairnessIndicatorDonut
                      v-for="indicator in groupedIndicators.findability"
                      :key="indicator.id"
                      :indicator="indicator"
                    />
                  </div>
                </section>

                <section v-if="groupedIndicators.access.length">
                  <h3 class="text-sm font-semibold text-secondary-800 mb-3">
                    Access &amp; releases
                  </h3>
                  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    <FairnessIndicatorDonut
                      v-for="indicator in groupedIndicators.access"
                      :key="indicator.id"
                      :indicator="indicator"
                    />
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      </Card>
      <Card
        v-else-if="error && !isLoading"
        padding="p-6 sm:p-8"
        custom-class="rounded-xl border-red-200 bg-red-50/50"
      >
        <p class="text-red-700 font-medium">
          Extraction failed
        </p>
        <p class="mt-2 text-sm text-red-600">
          {{ error }}
        </p>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ExtractionStreamResult, ExtractionProgress } from '../../composables/useApi'
import { useApi } from '../../composables/useApi'
import { useExtractionStore } from '../../stores/extraction'
import { useFairnessStore } from '../../stores/fairness'

const extractionStore = useExtractionStore()
const fairnessStore = useFairnessStore()

const repoUrl = computed({
  get: () => extractionStore.repoUrl,
  set: (v: string) => { extractionStore.repoUrl = v },
})

const schema = computed<'maSMP' | 'CodeMeta'>({
  get: () => extractionStore.schema,
  set: (v) => { extractionStore.schema = v },
})

const accessToken = computed({
  get: () => extractionStore.accessToken,
  set: (v: string) => { extractionStore.accessToken = v },
})

const runFairness = ref(false)

const isLoading = ref(false)
const error = computed({
  get: () => extractionStore.error,
  set: (v: string) => { extractionStore.error = v },
})
const showTokenTip = ref(false)
const tokenTipTab = ref<'github' | 'gitlab'>('github')
const progressQueue = ref<ExtractionProgress[]>([])
const extractionKey = ref(0) // Used to reset ExtractionProgress component when starting a new extraction
const extractionResult = computed<ExtractionStreamResult | null>({
  get: () => extractionStore.result,
  set: (v) => { extractionStore.result = v as ExtractionStreamResult | null },
})

const fairness = computed(() => fairnessStore.fairness)
const fairnessError = computed(() => fairnessStore.error)

const resultsTabs = [
  { key: 'metadata' as const, label: 'Metadata' },
  { key: 'fairness' as const, label: 'FAIRness' },
]
const activeResultsTab = ref<'metadata' | 'fairness'>('metadata')

const groupedIndicators = computed(() => {
  const indicators = (fairness.value?.indicators || []) as any[]
  const byIds = (ids: string[]) => indicators.filter((i) => ids.includes(i.id))
  return {
    documentation: byIds([
      'bp1_description_present',
      'bp5_usage_documentation',
      'bp6_license_declared',
      'bp7_explicit_citation',
      'bp9_install_instructions',
      'bp10_software_requirements',
    ]),
    findability: byIds([
      'bp2_persistent_identifier',
      'bp8_software_metadata',
    ]),
    access: byIds([
      'bp3_download_url_available',
      'bp4_semver_like_version',
    ]),
  }
})

useHead({
  title: 'Extract metadata - CoMET-RS',
})

const onExtract = async () => {
  error.value = ''
  extractionResult.value = null
  fairnessStore.clear()
  activeResultsTab.value = 'metadata'
  extractionKey.value++ // Reset ExtractionProgress component to clear previous progress
  isLoading.value = true
  progressQueue.value = []
  try {
    const { extractMetadataStream, getFairness } = useApi()
    const result = await extractMetadataStream(
      repoUrl.value,
      schema.value,
      accessToken.value || undefined,
      (p) => { progressQueue.value.push(p) }
    )
    extractionStore.setForm(repoUrl.value, schema.value, accessToken.value)
    extractionStore.setResult(result)
    // Keep overlay visible briefly so the user sees the last step (e.g. jsonld_build) as completed
    await new Promise((r) => setTimeout(r, 500))

    if (runFairness.value) {
      const { data, error: fairnessError } = await getFairness(
        repoUrl.value,
        schema.value,
        accessToken.value || undefined
      )
      if (fairnessError) {
        fairnessStore.setError(fairnessError)
      } else if (data && (data as any).fairness) {
        fairnessStore.setForm(repoUrl.value, schema.value, accessToken.value)
        fairnessStore.setFairness((data as any).fairness)
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Extraction failed'
  } finally {
    isLoading.value = false
  }
}
</script>
