export interface User {
  id: number;
  username: string;
  email: string;
  daily_total: number;
}

export interface Paper {
  id: number;
  title: string;
  authors: any;
  venue: string | null;
  venue_hint: string | null;
  year: number;
  abstract_en?: string;
  abstract_cn?: string;
  summary_cn?: {
    title_cn?: string;
    abstract_cn?: string;
    summary_cn?: {
      core_issue?: string;
      innovation?: string;
      key_method?: string;
      experiment_highlights?: string;
      recommendation_reason?: string;
    };
  };
  comments?: string | null;
  url?: string;
  pdf_url?: string;
  arxiv_id?: string | null;
  doi?: string | null;
  citation_count?: number;
  source: string;
  keyword_score: number;
  personal_score: number;
  prefilter_score: number;
  llm_score: number;
  final_score: number;
  llm_reason?: string | null;
  bucket: 'venue' | 'arxiv' | null;
  pushed?: boolean;
  created_at: string;
  tag_type?: 'interested' | 'not_interested' | 'read_later' | null;
}

export interface Keyword {
  id: number;
  keyword: string;
  weight: number;
  category: 'topic' | 'method' | 'system' | string;
  aliases: string[] | null;
  source: 'manual' | 'feedback' | 'preset' | string;
}

export interface BucketConfig {
  name: string;
  enabled: boolean;
  quota: number;
  venues?: string[];
  include_dblp?: boolean;
  include_venue_hint?: boolean;
  arxiv_categories?: string[];
}

export interface SystemConfig {
  sources: {
    daily_total: number;
    fill_policy: 'strict' | 'spillover' | string;
    oversample: number;
    buckets: BucketConfig[];
  };
  scoring: {
    prefilter: {
      keyword: number;
      personal: number;
      recency: number;
      source_prior: number;
    };
  };
  recommender: {
    min_pos_centroid: number;
    min_pos_model: number;
    min_neg_model: number;
  };
  llm: {
    chain: string[];
    daily_budget: number;
    max_cost_per_call: number;
    batch_size: number;
    circuit_threshold: number;
    circuit_cooldown_sec: number;
  };
  scheduler: {
    digest_cron: string;
    fetch_cron: string;
  };
  smtp?: {
    host: string;
    port: number;
    username: string;
    use_tls: boolean;
    sender: string;
  };
}

export interface DigestHistory {
  date: string;
  papers: Partial<Paper>[];
  bucket_breakdown: Record<string, number>;
  channel: string;
  status: 'sent' | 'failed' | 'degraded' | string;
  degraded: boolean;
  created_at: string | null;
}
