<template>
  <div class="paper-detail-view">
    <n-spin :show="loading">
      <div v-if="error" class="error-container">
        <n-result status="500" title="无法加载论文" description="论文不存在，或服务器发生错误">
          <template #footer>
            <n-button @click="goBack">返回上一页</n-button>
          </template>
        </n-result>
      </div>

      <div v-else-if="paper" class="detail-container">
        <!-- Header -->
        <div class="detail-header">
          <n-button secondary @click="goBack" style="margin-bottom: 12px;">
            &larr; 返回
          </n-button>
          
          <h1 class="title-cn">{{ paper.summary_cn?.title_cn || paper.title }}</h1>
          <h3 v-if="paper.summary_cn?.title_cn" class="title-en">{{ paper.title }}</h3>
          
          <div class="authors">
            <strong>作者:</strong> {{ formatAuthors(paper.authors) }}
          </div>

          <n-space style="margin-top: 12px;">
            <n-tag :type="bucketType">{{ bucketLabel }}</n-tag>
            <n-tag v-if="venueLabel" type="warning">{{ venueLabel }}</n-tag>
            <n-tag v-if="paper.arxiv_id" type="info">arXiv: {{ paper.arxiv_id }}</n-tag>
            <n-tag v-if="paper.doi" type="success">DOI: {{ paper.doi }}</n-tag>
            <n-tag v-if="paper.citation_count !== undefined" type="default">
              引用数: {{ paper.citation_count }}
            </n-tag>
          </n-space>
        </div>

        <!-- Main Body split: Left summary/abstracts, Right Scores/Actions -->
        <n-grid cols="1 s:1 m:3 l:3" responsive="screen" :x-gap="16" :y-gap="16">
          <!-- Left Main Content Column -->
          <n-grid-item span="2">
            <n-space vertical size="large">
              <!-- CN Summary section if present -->
              <n-card v-if="hasSummary" title="💡 AI 结构化精读" bordered>
                <n-collapse :default-expanded-names="['core', 'method', 'innovation', 'highlight', 'reason']">
                  <n-collapse-item title="核心问题 (Core Issue)" name="core">
                    <p class="summary-text">{{ summaryDetails?.core_issue }}</p>
                  </n-collapse-item>
                  <n-collapse-item title="创新点 (Innovation)" name="innovation">
                    <p class="summary-text">{{ summaryDetails?.innovation }}</p>
                  </n-collapse-item>
                  <n-collapse-item title="关键方法 (Key Method)" name="method">
                    <p class="summary-text">{{ summaryDetails?.key_method }}</p>
                  </n-collapse-item>
                  <n-collapse-item title="实验亮点 (Experiment Highlights)" name="highlight">
                    <p class="summary-text">{{ summaryDetails?.experiment_highlights }}</p>
                  </n-collapse-item>
                  <n-collapse-item title="推荐理由 (Recommendation Reason)" name="reason">
                    <p class="summary-text">{{ summaryDetails?.recommendation_reason }}</p>
                  </n-collapse-item>
                </n-collapse>
              </n-card>

              <!-- LLM reason if present -->
              <n-card v-if="paper.llm_reason" title="🤖 LLM 研判原因" bordered>
                <p style="white-space: pre-wrap; line-height: 1.6; color: #374151;">
                  {{ paper.llm_reason }}
                </p>
              </n-card>

              <!-- Translation/CN Abstract -->
              <n-card title="🇨🇳 中文摘要" bordered>
                <p class="abstract-text">
                  {{ paper.abstract_cn || '暂无中文翻译抽象' }}
                </p>
              </n-card>

              <!-- English Abstract -->
              <n-card title="🇬🇧 英文摘要 (Abstract)" bordered>
                <p class="abstract-text english">
                  {{ paper.abstract_en || 'No abstract text available.' }}
                </p>
              </n-card>

              <!-- Paper comments / metadata -->
              <n-card v-if="paper.comments" title="💬 arXiv 备注 (Comments)" bordered>
                <p style="font-family: monospace; font-size: 13px; color: #4b5563;">
                  {{ paper.comments }}
                </p>
              </n-card>
            </n-space>
          </n-grid-item>

          <!-- Right Sidebar Column -->
          <n-grid-item span="1">
            <n-space vertical size="large">
              <!-- Score breakdown component -->
              <n-card title="🎯 评分详情" bordered>
                <score-bar
                  :final-score="paper.final_score"
                  :keyword-score="paper.keyword_score"
                  :personal-score="paper.personal_score"
                  :prefilter-score="paper.prefilter_score"
                  :llm-score="paper.llm_score"
                />
              </n-card>

              <!-- User actions and feedback -->
              <n-card title="🛠️ 论文操作" bordered>
                <n-space vertical size="medium">
                  <div class="feedback-section">
                    <div style="font-weight: 500; font-size: 14px; margin-bottom: 8px; color: #475569;">
                      用户偏好标记:
                    </div>
                    <n-button-group style="width: 100%;">
                      <n-button
                        style="width: 33.3%;"
                        :type="currentTag === 'interested' ? 'success' : 'default'"
                        secondary
                        @click="toggleTag('interested')"
                      >
                        感兴趣
                      </n-button>
                      <n-button
                        style="width: 33.3%;"
                        :type="currentTag === 'not_interested' ? 'error' : 'default'"
                        secondary
                        @click="toggleTag('not_interested')"
                      >
                        不感兴趣
                      </n-button>
                      <n-button
                        style="width: 33.3%;"
                        :type="currentTag === 'read_later' ? 'info' : 'default'"
                        secondary
                        @click="toggleTag('read_later')"
                      >
                        稍后读
                      </n-button>
                    </n-button-group>
                  </div>

                  <n-divider style="margin: 12px 0;" />

                  <div class="link-section">
                    <n-space vertical>
                      <n-button
                        v-if="paper.pdf_url"
                        type="primary"
                        block
                        tag="a"
                        :href="paper.pdf_url"
                        target="_blank"
                      >
                        📄 打开 PDF 链接
                      </n-button>
                      <n-button
                        v-if="paper.url"
                        secondary
                        block
                        tag="a"
                        :href="paper.url"
                        target="_blank"
                      >
                        🔗 打开 网页 链接
                      </n-button>
                    </n-space>
                  </div>

                  <div class="meta-section" style="font-size: 12px; color: #64748b; margin-top: 12px;">
                    <div><strong>抓取来源:</strong> {{ paper.source }}</div>
                    <div><strong>录用年份:</strong> {{ paper.year }} 年</div>
                    <div v-if="paper.created_at">
                      <strong>收录日期:</strong> {{ formatDate(paper.created_at) }}
                    </div>
                    <div><strong>推送状态:</strong> {{ paper.pushed ? '已推送' : '未推送' }}</div>
                  </div>
                </n-space>
              </n-card>
            </n-space>
          </n-grid-item>
        </n-grid>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { Paper } from '../types';
import { papersApi } from '../api/papers';
import ScoreBar from '../components/ScoreBar.vue';
import { useMessage } from 'naive-ui';

const route = useRoute();
const router = useRouter();
const message = useMessage();

const paperId = Number(route.params.id);
const paper = ref<Paper | null>(null);
const loading = ref(false);
const error = ref(false);

const currentTag = ref<'interested' | 'not_interested' | 'read_later' | null>(null);

onMounted(() => {
  fetchPaper();
});

async function fetchPaper() {
  loading.value = true;
  error.value = false;
  try {
    const res = await papersApi.get(paperId);
    paper.value = res.data;
    currentTag.value = res.data.tag_type || null;
  } catch (err) {
    error.value = true;
    message.error('加载论文详情失败');
  } finally {
    loading.value = false;
  }
}

const bucketType = computed(() => {
  if (paper.value?.bucket === 'venue') return 'info';
  if (paper.value?.bucket === 'arxiv') return 'default';
  return 'warning';
});

const bucketLabel = computed(() => {
  if (paper.value?.bucket === 'venue') return '期刊会议';
  if (paper.value?.bucket === 'arxiv') return 'arXiv 预印本';
  return '未归桶';
});

const venueLabel = computed(() => {
  if (paper.value?.venue) {
    return `已见刊 ${paper.value.venue}`;
  }
  if (paper.value?.venue_hint) {
    return `录用指向 ${paper.value.venue_hint}`;
  }
  return null;
});

const hasSummary = computed(() => {
  return !!(
    paper.value?.summary_cn &&
    paper.value?.summary_cn.summary_cn
  );
});

const summaryDetails = computed(() => {
  return paper.value?.summary_cn?.summary_cn;
});

function formatAuthors(authors: any): string {
  if (!authors) return '';
  if (Array.isArray(authors)) {
    return authors.join(', ');
  }
  try {
    const parsed = typeof authors === 'string' ? JSON.parse(authors) : authors;
    if (Array.isArray(parsed)) {
      return parsed.join(', ');
    }
  } catch (e) {}
  return String(authors);
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  return dateStr.split('T')[0];
}

function goBack() {
  // If we can, return to router history, otherwise fallback to list
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push('/digest');
  }
}

async function toggleTag(tagType: 'interested' | 'not_interested' | 'read_later') {
  if (!paper.value) return;
  const targetTag = currentTag.value === tagType ? null : tagType;
  
  try {
    if (targetTag) {
      await papersApi.tag(paper.value.id, targetTag);
      currentTag.value = targetTag;
      message.success(`已标记为“${getTagName(targetTag)}”`);
    } else {
      await papersApi.removeTag(paper.value.id);
      currentTag.value = null;
      message.success('已取消标记');
    }
  } catch (e) {
    message.error('标记操作失败');
  }
}

function getTagName(tag: string): string {
  if (tag === 'interested') return '感兴趣';
  if (tag === 'not_interested') return '不感兴趣';
  if (tag === 'read_later') return '稍后读';
  return tag;
}
</script>

<style scoped>
.paper-detail-view {
  max-width: 1200px;
  margin: 0 auto;
}
.detail-header {
  background-color: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  margin-bottom: 16px;
  border: 1px solid #e2e8f0;
}
.title-cn {
  font-size: 24px;
  color: #0f172a;
  margin: 0 0 8px;
  line-height: 1.4;
}
.title-en {
  font-size: 18px;
  color: #475569;
  margin: 0 0 12px;
  font-weight: 500;
  line-height: 1.4;
}
.authors {
  color: #4b5563;
  font-size: 14px;
}
.summary-text {
  line-height: 1.6;
  color: #374151;
}
.abstract-text {
  line-height: 1.7;
  color: #374151;
  text-align: justify;
}
.abstract-text.english {
  color: #4b5563;
  font-style: italic;
}
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background-color: white;
  border-radius: 12px;
}
</style>
