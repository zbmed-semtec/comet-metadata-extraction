// composables/useApi.ts
import axios from 'axios'

// Local declaration so TypeScript recognizes Nuxt's runtime config helper
declare function useRuntimeConfig(): {
  public: {
    apiBase: string
  }
}

export interface ExtractionProgress {
  pipeline_size: number | null
  step: string
  status: 'started' | 'completed'
  label: string
}

export interface EnrichedProperty {
  confidence?: number | null
  source?: string | string[] | null
  category?: 'required' | 'recommended' | 'optional'
}

export interface ExtractionStreamResult {
  status: string
  schema: string
  code_url: string
  message: string
  results: Record<string, unknown>
  enriched_metadata: Record<string, Record<string, EnrichedProperty>>
}

export type ProgressCallback = (progress: ExtractionProgress) => void

export const useApi = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  const api = axios.create({
    baseURL: apiBase,
    headers: {
      'Content-Type': 'application/json'
    }
  })

  const extractMetadata = async (
    repoUrl: string,
    schema: string = 'maSMP',
    accessToken?: string
  ) => {
    try {
      const response = await api.get('/metadata', {
        params: {
          repo_url: repoUrl,
          schema,
          access_token: accessToken
        }
      })
      return { data: response.data, error: null }
    } catch (error: any) {
      return {
        data: null,
        error:
          error.response?.data?.detail ||
          error.message ||
          'An error occurred while extracting metadata'
      }
    }
  }

  const getFairness = async (
    repoUrl: string,
    schema: string = 'maSMP',
    accessToken?: string
  ) => {
    try {
      const response = await api.get('/api/fairness', {
        params: {
          repo_url: repoUrl,
          schema: schema === 'CodeMeta' ? 'CODEMETA' : schema,
          access_token: accessToken,
        },
      })
      return { data: response.data, error: null as string | null }
    } catch (error: any) {
      return {
        data: null as any,
        error:
          error.response?.data?.detail ||
          error.message ||
          'An error occurred while computing FAIRness',
      }
    }
  }

  /**
   * Extract metadata with live progress via SSE.
   * Calls onProgress for each step; returns full enriched result on success.
   */
  const extractMetadataStream = async (
    repoUrl: string,
    schema: string = 'maSMP',
    accessToken?: string,
    onProgress?: ProgressCallback
  ): Promise<ExtractionStreamResult> => {
    const params = new URLSearchParams({
      repo_url: repoUrl,
      schema: schema === 'CodeMeta' ? 'CODEMETA' : 'maSMP'
    })
    if (accessToken) params.set('access_token', accessToken)
    const url = `${apiBase}/api/metadata/stream?${params.toString()}`

    const response = await fetch(url, { headers: { Accept: 'text/event-stream' } })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || response.statusText || 'Extraction failed')
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')
    const decoder = new TextDecoder()
    let buffer = ''

    const processBuffer = (): ExtractionStreamResult | null => {
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        if (!block.trim()) continue
        const eventMatch = block.match(/^event:\s*(.+)$/m)
        const dataMatch = block.match(/^data:\s*(.+)$/ms)
        const event = eventMatch?.[1]?.trim() ?? ''
        const dataStr = dataMatch?.[1]?.trim()
        if (!dataStr) continue
        try {
          const data = JSON.parse(dataStr) as Record<string, unknown>
          if (event === 'progress' && onProgress) {
            onProgress({
              step: data.step as string,
              status: data.status as 'started' | 'completed',
              label: (data.label as string) ?? (data.step as string),
              pipeline_size: typeof data.pipeline_size === 'number' ? data.pipeline_size : null,
            })
          }
          if (event === 'result') return data as unknown as ExtractionStreamResult
          if (event === 'error') {
            const detail = (data as { detail?: string }).detail
            throw new Error(typeof detail === 'string' ? detail : 'Extraction failed')
          }
        } catch (e) {
          if (e instanceof Error) throw e
        }
      }
      return null
    }

    while (true) {
      const { done, value } = await reader.read()
      if (value) buffer += decoder.decode(value, { stream: true })
      const result = processBuffer()
      if (result) return result
      if (done) throw new Error('Stream ended without result')
    }
  }

  return {
    api,
    extractMetadata,
    extractMetadataStream,
    getFairness,
  }
}
