<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h2 class="text-xl font-semibold text-secondary-800">
        Extraction results
      </h2>
      <Button
        type="button"
        variant="secondary"
        size="small"
        custom-class="inline-flex items-center gap-2"
        @click="downloadJsonLd"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download JSON-LD
      </Button>
    </div>

    <!-- Required / Recommended / Optional sections; only shown when they have content -->
    <div class="space-y-8">
      <section
        v-for="cat in visibleCategories"
        :key="cat.key"
        class="rounded-xl border-2 overflow-hidden"
        :class="cat.sectionClass"
      >
        <header
          class="flex items-center gap-3 px-4 py-3 font-semibold"
          :class="cat.headerClass"
        >
          <span
            class="rounded-md px-2.5 py-1 text-xs font-bold uppercase tracking-wider"
            :class="cat.badgeClass"
          >
            {{ cat.key }}
          </span>
          <span :class="cat.titleClass">{{ cat.label }}</span>
        </header>
        <div class="border-t bg-white" :class="cat.borderClass">
          <ResultTable
            :rows="cat.rows"
            :show-source="true"
            :show-confidence="true"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ExtractionStreamResult, EnrichedProperty } from '../../composables/useApi'

const props = defineProps<{
  result: ExtractionStreamResult
}>()

const categoryConfig = [
  {
    key: 'Required',
    label: 'Must-have properties for this profile',
    sectionClass: 'border-amber-200 bg-amber-50/30',
    headerClass: 'bg-amber-50/80 text-amber-900',
    badgeClass: 'bg-amber-200 text-amber-800',
    titleClass: 'text-amber-900',
    borderClass: 'border-amber-100'
  },
  {
    key: 'Recommended',
    label: 'Recommended for richer metadata',
    sectionClass: 'border-primary-200 bg-primary-50/20',
    headerClass: 'bg-primary-50/80 text-primary-900',
    badgeClass: 'bg-primary-200 text-primary-800',
    titleClass: 'text-primary-900',
    borderClass: 'border-primary-100'
  },
  {
    key: 'Optional',
    label: 'Additional optional properties',
    sectionClass: 'border-slate-200 bg-slate-50/60',
    headerClass: 'bg-slate-100/80 text-slate-700',
    badgeClass: 'bg-slate-200 text-slate-600',
    titleClass: 'text-slate-700',
    borderClass: 'border-slate-100'
  }
] as const

export interface AuthorDisplayItem {
  name: string
  url?: string
}

export interface NamedLinkItem {
  name: string
  url?: string
}

export interface BibCardItem {
  title: string
  authors: string
  url?: string
}

/** The actual data object (flat map of property -> value). */
const resultData = computed<Record<string, unknown>>(() => {
  const data = props.result?.results
  return data && typeof data === 'object' && !Array.isArray(data) ? data as Record<string, unknown> : {}
})

/** The enriched metadata map (flat map of property -> { confidence, source, category }). */
const enrichedData = computed<Record<string, EnrichedProperty>>(() => {
  const data = props.result?.enriched_metadata
  return data && typeof data === 'object' && !Array.isArray(data) ? data as Record<string, EnrichedProperty> : {}
})

/** Only include categories that actually have at least one row (avoids empty CodeMeta sections). */
const visibleCategories = computed(() => {
  return categoryConfig
    .map(cat => ({ ...cat, rows: rowsByCategory(cat.key) }))
    .filter(cat => cat.rows.length > 0)
})

function rowsByCategory(category: string) {
  const data = resultData.value
  const enriched = enrichedData.value
  const skip = new Set(['@context', '@type'])
  const catLower = category.toLowerCase()

  return Object.entries(data)
    .filter(([k]) => !skip.has(k))
    .filter(([k]) => {
      const c = enriched[k]?.category
      // Only include a property under a category if it's *explicitly* tagged with that category.
      // Properties with no enrichment metadata / no category are not forced into "Optional".
      return typeof c === 'string' && c.toLowerCase() === catLower
    })
    .map(([prop, val]) => {
      const meta = enriched[prop]
      const authorItems = getAuthorItems(prop, val)
      const contributorItems = getContributorItems(prop, val)
      const namedLink = getNamedLink(prop, val)
      const bibCard = getBibCard(prop, val)
      const useSpecial = authorItems ?? contributorItems ?? namedLink ?? bibCard
      return {
        property: formatPropertyName(prop),
        value: useSpecial ? '' : formatValueForProperty(prop, val),
        source: meta?.source ?? '—',
        confidence: meta?.confidence != null ? `${Math.round(Number(meta.confidence) * 100)}%` : '—',
        ...(authorItems ? { authorItems } : {}),
        ...(contributorItems ? { contributorItems } : {}),
        ...(namedLink ? { namedLink } : {}),
        ...(bibCard ? { bibCard } : {})
      }
    })
}

function formatPropertyName(key: string): string {
  return key.replace(/^[^:]+:/, '').replace(/([A-Z])/g, ' $1').trim() || key
}

function getBibCard(prop: string, val: unknown): BibCardItem | null {
  const propLowerRaw = (formatPropertyName(prop) || prop).toLowerCase().replace(/\s+/g, '')
  const refKeys = ['referencepublication', 'citation']
  if (!refKeys.some(k => propLowerRaw.includes(k))) return null

  let refVal: unknown = val
  if (Array.isArray(val) && val.length > 0) {
    refVal = val[0]
  }
  if (refVal == null || typeof refVal !== 'object' || Array.isArray(refVal)) return null

  const ref = refVal as Record<string, unknown>
  const title = (ref.name ?? ref.title ?? '') as string
  if (!title || typeof title !== 'string' || !title.trim()) return null
  const authors = formatRefAuthors(ref.author)
  let url: string | undefined
  const rawId = (ref['@id'] ?? ref.id ?? ref.url ?? ref.doi ?? '') as string
  if (rawId && typeof rawId === 'string' && rawId.trim()) {
    url = /^https?:\/\//i.test(rawId) ? rawId : (rawId.startsWith('doi.org') ? `https://${rawId}` : `https://doi.org/${rawId.replace(/^\/+/, '')}`)
  }
  return { title: title.trim(), authors: authors || '—', ...(url ? { url } : {}) }
}

function formatRefAuthors(author: unknown): string {
  if (author == null) return ''
  const list = Array.isArray(author) ? author : [author]
  const names: string[] = []
  for (const item of list) {
    if (item == null || typeof item !== 'object') continue
    const p = item as Record<string, unknown>
    const given = (p.givenName ?? p.given_name ?? '') as string
    const family = (p.familyName ?? p.family_name ?? '') as string
    const name = (p.name as string) ?? [given, family].filter(Boolean).join(' ').trim()
    if (name && typeof name === 'string') names.push(name.trim())
    else if (given || family) names.push([given, family].filter(Boolean).join(' ').trim())
  }
  if (names.length === 0) return ''
  if (names.length === 1) return names[0]
  if (names.length === 2) return `${names[0]} and ${names[1]}`
  return `${names.slice(0, -1).join(', ')}, and ${names[names.length - 1]}`
}

function getNamedLink(prop: string, val: unknown): NamedLinkItem | null {
  const propLower = (formatPropertyName(prop) || prop).toLowerCase()
  if (propLower !== 'license' && propLower !== 'identifier' && propLower !== 'version control system') return null
  if (val == null || typeof val !== 'object' || Array.isArray(val)) return null
  const o = val as Record<string, unknown>
  const name = (o.name ?? o.title ?? '') as string
  if (!name || typeof name !== 'string' || !name.trim()) return null
  let url: string | undefined
  const raw = (o.url ?? o['@id'] ?? o.id ?? '') as string
  if (raw && typeof raw === 'string' && raw.trim()) {
    url = /^https?:\/\//i.test(raw) ? raw : `https://${raw.replace(/^\/+/, '')}`
  }
  return { name: name.trim(), ...(url ? { url } : {}) }
}

function getAuthorItems(prop: string, val: unknown): AuthorDisplayItem[] | null {
  const propLower = (formatPropertyName(prop) || prop).toLowerCase()
  if (propLower !== 'author') return null
  if (val == null) return null
  const list = Array.isArray(val) ? val : (typeof val === 'object' && val !== null ? [val] : null)
  if (!list?.length) return null
  const items: AuthorDisplayItem[] = []
  for (const item of list) {
    const one = toAuthorDisplayItem(item)
    if (one) items.push(one)
  }
  return items.length ? items : null
}

function getContributorItems(prop: string, val: unknown): AuthorDisplayItem[] | null {
  const propLower = (formatPropertyName(prop) || prop).toLowerCase()
  if (propLower !== 'contributor') return null
  if (val == null) return null
  const list = Array.isArray(val) ? val : (typeof val === 'object' && val !== null ? [val] : null)
  if (!list?.length) return null
  const items: AuthorDisplayItem[] = []
  for (const item of list) {
    const one = toContributorDisplayItem(item)
    if (one) items.push(one)
  }
  return items.length ? items : null
}

function labelFromUrl(url: string): string {
  try {
    const u = new URL(url)
    const path = u.pathname.replace(/^\/+/, '').split('/').filter(Boolean)
    if (path.length === 0) return u.hostname
    if (path.length === 1) return path[0]
    if (path[0] === 'apps') return path[1] ?? path[0]
    return path[path.length - 1]
  } catch {
    return url.length > 40 ? url.slice(0, 37) + '…' : url
  }
}

function toContributorDisplayItem(person: unknown): AuthorDisplayItem | null {
  if (person == null || typeof person !== 'object') return null
  const p = person as Record<string, unknown>

  const name = (p.name ?? p['https://schema.org/name'] ?? '') as string
  const given = (p.givenName ?? p.given_name ?? '') as string
  const family = (p.familyName ?? p.family_name ?? '') as string
  const fullName = (name && name.trim()) || [given, family].filter(Boolean).join(' ').trim()

  if (fullName) {
    let url: string | undefined
    const rawId = (p['@id'] ?? p.id ?? p.url ?? '') as string
    if (rawId && typeof rawId === 'string' && rawId.trim()) {
      url = /^https?:\/\//i.test(rawId) ? rawId : rawId
    }
    return { name: fullName, ...(url ? { url } : {}) }
  }

  const rawUrl = (p.url ?? p['@id'] ?? p.id ?? '') as string
  if (!rawUrl || typeof rawUrl !== 'string' || !rawUrl.trim()) return null
  const url = /^https?:\/\//i.test(rawUrl) ? rawUrl : `https://${rawUrl.replace(/^\/+/, '')}`
  const label = labelFromUrl(url)
  return { name: label, url }
}

function formatValueForProperty(prop: string, val: unknown): string {
  const propLower = (formatPropertyName(prop) || prop).toLowerCase()
  if (propLower === 'author') return formatAuthor(val)
  return formatValue(val)
}

function toAuthorDisplayItem(person: unknown): AuthorDisplayItem | null {
  if (person == null || typeof person !== 'object') return null
  const p = person as Record<string, unknown>
  const name = (p.name ?? p['https://schema.org/name'] ?? '') as string
  const given = (p.givenName ?? p.given_name ?? '') as string
  const family = (p.familyName ?? p.family_name ?? '') as string
  const fullName = (name && name.trim()) || [given, family].filter(Boolean).join(' ').trim()
  if (!fullName) return null
  let url: string | undefined
  const rawId = (p['@id'] ?? p.id ?? p.url ?? '') as string
  if (rawId && typeof rawId === 'string' && rawId.trim()) {
    url = /^https?:\/\//i.test(rawId) ? rawId : (rawId.startsWith('orcid.org') ? `https://${rawId}` : rawId)
  }
  return { name: fullName, ...(url ? { url } : {}) }
}

function formatValue(val: unknown): string {
  if (val == null) return '—'
  if (typeof val === 'string') return val
  if (typeof val === 'number' || typeof val === 'boolean') return String(val)
  if (Array.isArray(val)) return val.map(v => formatValue(v)).join(', ')
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

function formatAuthor(val: unknown): string {
  if (val == null) return '—'
  if (Array.isArray(val)) {
    const lines = val.map(item => formatOneAuthor(item)).filter(Boolean)
    return lines.length ? lines.join('\n') : '—'
  }
  if (typeof val === 'object' && val !== null) return formatOneAuthor(val as Record<string, unknown>)
  return formatValue(val)
}

function formatOneAuthor(person: unknown): string {
  if (person == null || typeof person !== 'object') return ''
  const p = person as Record<string, unknown>
  const name = (p.name ?? p['https://schema.org/name'] ?? '') as string
  const given = (p.givenName ?? p.given_name ?? '') as string
  const family = (p.familyName ?? p.family_name ?? '') as string
  const fullName = (name && name.trim()) || [given, family].filter(Boolean).join(' ').trim()
  if (!fullName) return ''

  let id = (p['@id'] ?? p.id ?? '') as string
  if (id && typeof id === 'string' && !/^https?:\/\//i.test(id)) id = id.startsWith('orcid.org') ? `https://${id}` : id

  if (id && typeof id === 'string' && id.trim()) return `${fullName} (${id})`
  return fullName
}

function downloadJsonLd() {
  const blob = new Blob([JSON.stringify(props.result.results, null, 2)], { type: 'application/ld+json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `metadata-${props.result.schema ?? 'export'}-${Date.now()}.jsonld`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
