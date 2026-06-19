<template>
  <n-card class="paper-card" hoverable :title="displayTitle">
    <template #header-extra>
      <div style="display: flex; gap: 8px; align-items: center;">
        <n-tag :type="bucketType" size="small">{{ bucketLabel }}</n-tag>
        <n-tag v-if="venueLabel" type="warning" size="small">{{ venueLabel }}</n-tag>
        <span class="score-badge">{{ paper.final_score.toFixed(2) }}分</span>
      </div>
    </template>

    <div class="authors">
      {{ formatAuthors(paper.authors) }}
    </div>

    <!-- Brief summary if present, otherwise english abstract -->
    <div class="abstract-section">
      <div v-if="hasSummary" class="cn-summary">
        <div class="summary-item">
          <strong>核心问题: </strong>
          <span>{{ summaryDetails?.core_issue }}</span>
        </div>
        <div class="summary-item">
          <strong>创新方法: </strong>
          <span>{{ summaryDetails?.key_method }}</span>
        </div>
      </div>
      <p v-else class="abstract-en">
        {{ truncate(paper.abstract_cn || paper.abstract_en || '', 200) }}
      </p>
    </div>

    <template #footer>
      <div class="footer-row">
        <div class="tag-actions">
          <n-button-group size="small">
            <n-button
              :type="currentTag === 'interested' ? 'success' : 'default'"
              secondary
              @click="toggleTag('interested')"
            >
              感兴趣
            </n-button>
            <n-button
              :type="currentTag === 'not_interested' ? 'error' : 'default'"
              secondary
              @click="toggleTag('not_interested')"
            >
              不感兴趣
            </n-button>
            <n-button
              :type="currentTag === 'read_later' ? 'info' : 'default'"
              secondary
              @click="toggleTag('read_later')"
            >
              稍后读
            </n-button>
          </n-button-group>
        </div>
        <div class="navigation-actions">
          <n-button size="small" type="primary" text @click="goToDetail">
            查看详情 &rarr;
          </n-button>
        </div>
      </div>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import type { Paper } from '../types';
import { papersApi } from '../api/papers';
import { useMessage } from 'naive-ui';

const props = defineProps<{
  paper: Paper;
}>();

const emit = defineEmits<{
  (e: 'tag-updated', paperId: number, newTag: string | null): void;
}>();

const router = useRouter();
const message = useMessage();

const currentTag = ref<'interested' | 'not_interested' | 'read_later' | null>(
  props.paper.tag_type || null
);

// If backend doesn't populate paper.tag_type directly on list endpoint, we can load or respect what is passed.
// Wait, is tag_type passed directly? We'll see.
onMounted(() => {
  currentTag.value = props.paper.tag_type || null;
});

const displayTitle = computed(() => {
  // If translated title exists, show it, otherwise English title.
  return props.paper.summary_cn?.title_cn || props.paper.title;
});

const bucketType = computed(() => {
  if (props.paper.bucket === 'venue') return 'info';
  if (props.paper.bucket === 'arxiv') return 'default';
  return 'warning';
});

const bucketLabel = computed(() => {
  if (props.paper.bucket === 'venue') return '期刊会议';
  if (props.paper.bucket === 'arxiv') return 'arXiv预印本';
  return '未归桶';
});

const venueLabel = computed(() => {
  if (props.paper.venue) {
    return `已见刊 ${props.paper.venue}`;
  }
  if (props.paper.venue_hint) {
    return `录用指向 ${props.paper.venue_hint}`;
  }
  return null;
});

const hasSummary = computed(() => {
  return !!(
    props.paper.summary_cn &&
    props.paper.summary_cn.summary_cn
  );
});

const summaryDetails = computed(() => {
  return props.paper.summary_cn?.summary_cn;
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

function truncate(str: string, len: number): string {
  if (str.length <= len) return str;
  return str.slice(0, len) + '...';
}

async function toggleTag(tagType: 'interested' | 'not_interested' | 'read_later') {
  const targetTag = currentTag.value === tagType ? null : tagType;
  
  try {
    if (targetTag) {
      await papersApi.tag(props.paper.id, targetTag);
      currentTag.value = targetTag;
      message.success(`已标记为“${getTagName(targetTag)}”`);
    } else {
      await papersApi.removeTag(props.paper.id);
      currentTag.value = null;
      message.success('已取消标记');
    }
    emit('tag-updated', props.paper.id, targetTag);
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

function goToDetail() {
  router.push(`/papers/${props.paper.id}`);
}
</script>

<style scoped>
.paper-card {
  margin-bottom: 16px;
  border-radius: 12px;
}
.score-badge {
  font-weight: 700;
  color: #1e293b;
  font-size: 14px;
}
.authors {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 12px;
}
.abstract-section {
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
}
.cn-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background-color: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
}
.summary-item {
  margin-bottom: 2px;
}
.abstract-en {
  color: #475569;
  font-style: italic;
}
.footer-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
