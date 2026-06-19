export interface User {
  id: number
  username: string
  email: string
  daily_total: number
}

export interface Paper {
  id: number
  title: string
  authors: string[]
  venue: string | null
  venue_hint: string | null
  year: number | null
  abstract_en: string | null
  abstract_cn: string | null
  summary_cn: PaperSummary | null
  comments: string | null
  url: string | null
  pdf_url: string | null
  arxiv_id: string | null
  doi: string | null
  citation_count: number
  source: string
  keyword_score: number
  personal_score: number
  prefilter_score: number
  llm_score: number | null
  final_score: number
  llm_reason: string | null
  bucket: string | null
  pushed: boolean
  created_at: string | null
  tag_type?: string | null
}

export interface PaperSummary {
  core_issue?: string
  innovation?: string
  key_method?: string
  experiment_highlights?: string
  recommendation_reason?: string
}

export interface PaperListItem {
  id: number
  title: string
  authors: string[]
  venue: string | null
  venue_hint: string | null
  year: number | null
  abstract_cn: string | null
  arxiv_id: string | null
  final_score: number
  keyword_score: number
  bucket: string | null
  source: string
  created_at: string | null
}

export interface ListPapersResponse {
  items: PaperListItem[]
  total: number
  page: number
  pages: number
}

export interface Keyword {
  id: number
  keyword: string
  weight: number
  category: string
  aliases: string[] | null
  source: string
}

export interface DigestHistory {
  date: string
  papers: DigestPaper[]
  bucket_breakdown: Record<string, number[]> | null
  channel: string
  status: string
  degraded: boolean
  created_at: string | null
}

export interface DigestPaper {
  id: number
  title: string
  title_cn: string | null
  abstract_cn: string | null
  summary_cn: PaperSummary | null
  venue: string | null
  venue_hint: string | null
  year: number | null
  pdf_url: string | null
  url: string | null
  final_score: number
  bucket: string | null
  created_at: string | null
  tag_type?: string | null
}

export interface BucketConfig {
  name: string
  enabled: boolean
  quota: number
  venues?: string[]
  arxiv_categories?: string[]
  include_dblp?: boolean
  include_venue_hint?: boolean
}

export interface SystemConfig {
  sources: {
    daily_total: number
    fill_policy: string
    oversample: number
    buckets: BucketConfig[]
  }
  scoring: {
    prefilter: {
      keyword: number
      personal: number
      recency: number
      source_prior: number
    }
  }
  recommender: {
    min_pos_centroid: number
    min_pos_model: number
    min_neg_model: number
  }
  llm: {
    chain: string[]
    daily_budget: number
    max_cost_per_call: number
    batch_size: number
    circuit_threshold: number
    circuit_cooldown_sec: number
  }
  scheduler: {
    digest_cron: string
    fetch_cron: string
  }
}

export type TagType = 'interested' | 'not_interested' | 'read_later'
