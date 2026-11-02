<template>
  <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
    <div class="overflow-x-auto">
      <table class="result-table min-w-full divide-y divide-gray-200 text-left text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="result-table-property px-4 py-3 font-medium text-gray-700">
              Property
            </th>
            <th scope="col" class="result-table-value px-4 py-3 font-medium text-gray-700">
              Value
            </th>
            <th
              v-if="showSource"
              scope="col"
              class="result-table-source px-4 py-3 font-medium text-gray-700 hidden sm:table-cell"
            >
              Source
            </th>
            <th
              v-if="showSourceReliability"
              scope="col"
              class="result-table-source-reliability px-4 py-3 font-medium text-gray-700 hidden sm:table-cell"
            >
              Source reliability
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 bg-white">
          <tr
            v-for="(row, i) in rows"
            :key="i"
            class="hover:bg-gray-50/80"
          >
            <td class="result-table-property px-4 py-3 font-medium text-secondary-800">
              {{ row.property }}
            </td>
            <td class="result-table-value max-w-0 px-4 py-3 text-gray-700 align-top">
              <span class="inline-flex flex-wrap items-baseline gap-x-1.5 gap-y-1.5 break-words">
                <!-- Author / contributor row: links in blue, non-links in rose -->
                <template v-if="(row.authorItems ?? row.contributorItems)?.length">
                  <template v-for="(author, ai) in (row.authorItems ?? row.contributorItems)" :key="ai">
                    <a
                      v-if="author.url"
                      :href="author.url"
                      :title="author.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2 py-1 text-sm text-blue-700 no-underline ring-1 ring-blue-200/60 hover:bg-blue-100 hover:ring-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {{ author.name }}
                      <svg class="h-3.5 w-3.5 shrink-0 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                    <span
                      v-else
                      class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-sm text-green-700 ring-1 ring-green-200/60"
                    >
                      {{ author.name }}
                    </span>
                  </template>
                </template>
                <!-- Reference publication: bib card (title, authors, optional link) -->
                <template v-else-if="row.bibCard">
                  <div class="rounded-lg border border-green-200 bg-green-50/60 px-3 py-2.5 text-left shadow-sm">
                    <div class="font-medium text-slate-900">
                      <a
                        v-if="row.bibCard.url"
                        :href="row.bibCard.url"
                        :title="row.bibCard.url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-700 no-underline hover:text-blue-800 hover:underline"
                      >{{ row.bibCard.title }}</a>
                      <span v-else class="text-green-800">{{ row.bibCard.title }}</span>
                    </div>
                    <div class="mt-1 text-sm text-green-700">
                      {{ row.bibCard.authors }}
                    </div>
                  </div>
                </template>
                <!-- License / identifier: show name only, link to URL when present -->
                <template v-else-if="row.namedLink">
                  <a
                    v-if="row.namedLink.url"
                    :href="row.namedLink.url"
                    :title="row.namedLink.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2 py-1 text-sm text-blue-700 no-underline ring-1 ring-blue-200/60 hover:bg-blue-100 hover:ring-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {{ row.namedLink.name }}
                    <svg class="h-3.5 w-3.5 shrink-0 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                  <span
                    v-else
                    class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-sm text-green-700 ring-1 ring-green-200/60"
                  >
                    {{ row.namedLink.name }}
                  </span>
                </template>
                <!-- Default: URLs, lists, plain text -->
                <template v-else>
                  <!-- For description, always show as a single text block (no list / pill splitting) -->
                  <template v-if="isDescription(row.property)">
                    <span
                      class="inline-block rounded-md bg-green-50 px-2.5 py-1.5 text-green-800 ring-1 ring-green-200/70 whitespace-pre-wrap break-words"
                    >
                      {{ row.value }}
                    </span>
                  </template>
                  <!-- For certain properties (e.g. copyright holder), keep a single text block but make URLs clickable -->
                  <template v-else-if="isTextBlockWithLinks(row.property)">
                    <span
                      class="inline-block rounded-md bg-green-50 px-2.5 py-1.5 text-green-800 ring-1 ring-green-200/70 whitespace-pre-wrap break-words"
                    >
                      <template v-for="(part, i) in parseValue(row.value)" :key="i">
                        <a
                          v-if="part.type === 'url'"
                          :href="part.href"
                          :title="part.href"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="text-blue-700 underline decoration-blue-400 hover:text-blue-800 hover:decoration-blue-600"
                        >
                          {{ formatUrlLabel(part.href) }}
                        </a>
                        <span v-else>{{ part.content }}</span>
                      </template>
                    </span>
                  </template>
                  <!-- All other properties keep the richer URL + list formatting -->
                  <template v-else>
                    <template v-for="(part, i) in parseValue(row.value)" :key="i">
                      <a
                        v-if="part.type === 'url'"
                        :href="part.href"
                        :title="part.href"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2 py-1 text-blue-700 no-underline ring-1 ring-blue-200/60 hover:bg-blue-100 hover:ring-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-full min-w-0"
                      >
                        <span class="truncate">{{ formatUrlLabel(part.href) }}</span>
                        <svg class="h-3.5 w-3.5 shrink-0 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                      <template v-else-if="parseList(part.content)">
                        <span
                          v-for="(item, j) in parseList(part.content)"
                          :key="j"
                          class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-sm text-green-700 ring-1 ring-green-200/60"
                        >
                          {{ item }}
                        </span>
                      </template>
                      <span
                        v-else
                        class="inline-block rounded-md bg-green-50 px-2.5 py-1.5 text-green-800 ring-1 ring-green-200/70 whitespace-pre-wrap break-words"
                      >{{ part.content }}</span>
                    </template>
                  </template>
                </template>
              </span>

              <!-- Mobile: inline source and source-reliability chips below the value -->
              <div
                v-if="(showSource || showSourceReliability) && (row.source || row.source_reliability)"
                class="mt-2 flex flex-wrap gap-2 sm:hidden"
              >
                <template v-if="showSource">
                  <span
                    v-for="(src, si) in normalizeSources(row.source)"
                    :key="si"
                    class="inline-flex items-center rounded-md px-2 py-0.5 text-[0.7rem] font-medium ring-1"
                    :class="sourceTagClasses(src)"
                  >
                    {{ formatSourceLabel(src) }}
                  </span>
                </template>
                <span
                  v-if="showSourceReliability"
                  class="inline-flex items-center rounded-md bg-primary-50 px-2 py-0.5 text-[0.7rem] font-medium text-primary-700"
                >
                  {{ row.source_reliability }}
                </span>
              </div>
            </td>
            <td v-if="showSource" class="result-table-source px-4 py-3 hidden sm:table-cell">
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="(src, si) in normalizeSources(row.source)"
                  :key="si"
                  class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1"
                  :class="sourceTagClasses(src)"
                >
                  {{ formatSourceLabel(src) }}
                </span>
              </div>
            </td>
            <td v-if="showSourceReliability" class="result-table-source-reliability px-4 py-3 hidden sm:table-cell">
              <span
                class="inline-flex items-center rounded-md bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700"
              >
                {{ row.source_reliability }}
              </span>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td :colspan="showSource && showSourceReliability ? 4 : 2" class="px-4 py-6 text-center text-gray-500">
              No properties in this section.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    rows: {
      property: string
      value: string
      source: string | string[]
      source_reliability: string
      authorItems?: { name: string; url?: string }[]
      contributorItems?: { name: string; url?: string }[]
      namedLink?: { name: string; url?: string }
      bibCard?: { title: string; authors: string; url?: string }
    }[]
    showSource: boolean
    showSourceReliability: boolean
  }>(),
  { showSource: true, showSourceReliability: true }
)

const URL_REGEX = /(https?:\/\/[^\s<>"']+)/g

type ValuePart = { type: 'text'; content: string } | { type: 'url'; content: string; href: string }

function parseValue(value: string): ValuePart[] {
  if (!value || typeof value !== 'string') return [{ type: 'text', content: value ?? '' }]
  const parts: ValuePart[] = []
  let lastIndex = 0
  const re = new RegExp(URL_REGEX.source, 'g')
  let m: RegExpExecArray | null
  while ((m = re.exec(value)) !== null) {
    const raw = m[1]
    if (!raw) continue
    if (m.index > lastIndex) {
      const between = value.slice(lastIndex, m.index).trim()
      if (between) {
        parts.push({ type: 'text', content: between })
      }
    }
    const href = raw.replace(/[.,;?!)]+$/, '')
    parts.push({ type: 'url', content: raw, href })
    lastIndex = re.lastIndex
  }
  if (lastIndex < value.length) {
    const remaining = value.slice(lastIndex).trim()
    if (remaining) {
      parts.push({ type: 'text', content: remaining })
    }
  }
  return parts.length ? parts : [{ type: 'text', content: value }]
}


function isDescription(property: string): boolean {
  return (property || '').trim().toLowerCase() === 'description'
}

/** Properties that should render as a single text block with inline clickable URLs. */
function isTextBlockWithLinks(property: string): boolean {
  const key = (property || '').trim().toLowerCase().replace(/\s+/g, ' ')
  // Extend this list if other long-text properties should keep paragraph-style layout
  const textBlockProps = ['copyright holder']
  return textBlockProps.includes(key)
}

function formatUrlLabel(href: string): string {
  try {
    const url = new URL(href)
    const host = url.hostname.replace(/^www\./, '')
    const path = url.pathname === '/' ? '' : url.pathname
    const label = host + path
    return label.length > 50 ? label.slice(0, 47) + '…' : label
  } catch {
    return href.length > 50 ? href.slice(0, 47) + '…' : href
  }
}

/** If the text looks like a comma-separated list, return trimmed items; otherwise null. */
function parseList(text: string): string[] | null {
  if (!text || typeof text !== 'string') return null
  const trimmed = text.trim()
  if (!trimmed) return null
  const items = trimmed.split(/\s*,\s*/).map(s => s.trim()).filter(Boolean)
  if (items.length < 2) return null
  const maxItemLength = 120
  const looksLikeList = items.every(item => item.length <= maxItemLength)
  return looksLikeList ? items : null
}

/** Normalize source field (string or string[]) into an array of strings for display. */
function normalizeSources(source: string | string[] | undefined): string[] {
  if (Array.isArray(source)) return source.filter(Boolean)
  if (!source) return []
  return [source]
}

function sourceTagClasses(source: string): string {
  const s = (source || '').toLowerCase()
  // Outline-style chips with white background so they stand apart from
  // filled value (blue/green) and source-reliability (purple) chips.
  if (!s || s === '—') return 'bg-white text-slate-700 ring-slate-300'
  if (s === 'github_api' || s === 'gitlab_api') return 'bg-white text-sky-800 ring-2 ring-sky-400'
  if (s === 'citation_cff') return 'bg-white text-amber-900 ring-2 ring-amber-400'
  if (s === 'license_file') return 'bg-white text-orange-900 ring-2 ring-orange-400'
  if (s === 'readme_parser') return 'bg-white text-emerald-900 ring-2 ring-emerald-400'
  if (s === 'zenodo_badge' || s === 'wayback') return 'bg-white text-teal-900 ring-2 ring-teal-400'
  if (s === 'openalex') return 'bg-white text-cyan-900 ring-2 ring-cyan-400'
  if (s === 'llm') return 'bg-white text-fuchsia-900 ring-2 ring-fuchsia-400'
  return 'bg-white text-slate-800 ring-2 ring-slate-300'
}

function formatSourceLabel(source: string): string {
  const s = (source || '').toLowerCase()
  if (!s || s === '—') return '—'
  if (s === 'github_api') return 'GitHub API'
  if (s === 'gitlab_api') return 'GitLab API'
  if (s === 'citation_cff') return 'CFF File'
  if (s === 'license_file') return 'License File'
  if (s === 'readme_parser') return 'Readme'
  if (s === 'zenodo_badge') return 'Zenodo Badge'
  if (s === 'wayback') return 'Wayback Machine'
  if (s === 'software_heritage') return 'Software Heritage'
  if (s === 'openalex') return 'OpenAlex'
  if (s === 'llm') return 'LLM'
  return source
}
</script>

<style scoped>
.result-table {
  table-layout: fixed;
}
.result-table-property {
  width: 11rem;
}
.result-table-value {
  width: auto;
  min-width: 0;
}
.result-table-source {
  width: 8rem;
}
.result-table-source-reliability {
  width: 10rem;
}

@media (max-width: 640px) {
  .result-table {
    font-size: 0.8125rem;
  }
  .result-table-property {
    width: 7rem;
  }
  .result-table-source {
    width: 6rem;
  }
  .result-table-source-reliability {
    width: 7.5rem;
  }
}
</style>
