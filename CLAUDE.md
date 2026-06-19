# Paper Digest

AI 论文日报系统：每天自动从 arXiv 与顶会发现 LLM 存储/推理/AI基础设施方向论文，DeepSeek 打分排序 + 中文摘要，邮件推送；提供公网可访问的 Web 控制面板（mTLS 设备级认证）。

## 架构

```
Nginx (443, mTLS) → FastAPI backend (8000) → MySQL (外部容器)
                                            → DeepSeek / Kimi API
                                            → arXiv API
```

2 个 Docker 容器（backend + nginx），复用现有 VPS MySQL 容器。

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 async + asyncmy（MySQL）
- 认证：argon2id + JWT（httpOnly cookie）+ Nginx mTLS 客户端证书
- 推荐：TF-IDF 质心 → CalibratedLR（三段门控，按反馈量自动切换）
- 定时：APScheduler（内嵌 backend）
- 前端：Vue 3 + Naive UI + TypeScript + Vite（研究工具风格 UI，已完成主要页面统一）
- 邮件：aiosmtplib + Jinja2

## 目录结构

```
paper-digest/
├── Dockerfile.backend
├── docker-compose.yml          # backend + nginx；Phase 7 加 nginx 容器
├── .env.example                # 复制为 .env 后填写
├── certs/                      # TLS 证书（不入库）
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini + alembic/  # 数据库迁移
│   ├── config/default.json     # 默认配置（来源配额、LLM 预算、cron 时间等）
│   ├── scripts/
│   │   ├── init_db.py          # seed 唯一账号 + 默认配置（幂等）
│   │   ├── seed_keywords.py    # 加载关键词预设（Phase 3）
│   │   └── gen_client_cert.sh  # 自建 CA + 签设备证书（Phase 0）
│   ├── prompts/                # LLM 提示词（Phase 4）
│   ├── templates/email.html    # 邮件模板（Phase 5）
│   └── src/
│       ├── main.py             # FastAPI app + lifespan
│       ├── config.py           # 从环境变量读配置
│       ├── models.py           # SQLAlchemy ORM（6 张表）
│       ├── database.py         # async engine + session
│       ├── auth.py             # 密码哈希 / JWT / 限流 / 反馈 token
│       ├── scheduler.py        # APScheduler（Phase 7）
│       └── api/
│           ├── deps.py         # get_current_user（cookie JWT）
│           └── routes/
│               ├── auth.py     # /api/auth/login|logout|me
│               ├── papers.py   # Phase 2+
│               ├── digest.py   # Phase 5+
│               ├── feedback.py # Phase 5+
│               ├── keywords.py # Phase 3+
│               ├── settings.py # Phase 4+
│               ├── sources.py  # Phase 6+
└── frontend/                   # Vue 3 + Naive UI + TypeScript + Vite
    ├── package.json
    ├── vite.config.ts          # API 代理到 localhost:8000
    ├── README.md               # 前端结构、当前状态、下一步工作
    └── src/
        ├── main.ts             # 入口
        ├── App.vue             # Naive UI 主题配置
        ├── api/                # Axios 封装（client, auth, papers, digest, keywords, settings）
        ├── types/index.ts      # TypeScript 接口
        ├── stores/auth.ts      # Pinia 认证状态
        ├── router/index.ts     # 路由 + 鉴权守卫
        ├── components/         # AppLayout, PageHeader, PaperCard, TagButtonGroup, ScoreRing, SourceQuotaEditor, KeywordModal, EmptyState
        └── views/              # Login, Dashboard, Digest, Papers, PaperDetail, Keywords, Settings
```

## 快速启动（开发）

```bash
# 1. 环境准备
cp .env.example .env          # 填写 DATABASE_URL, JWT_SECRET, ADMIN_*
# MySQL 建库建用户（见 paper-digest-plan.md Phase 0）
# Docker 内连接外部 MySQL 时，DATABASE_URL 的 host 用 MySQL 容器名/网络别名，不用 127.0.0.1

# 2. 建表
cd backend
pip install -r requirements.txt
alembic upgrade head

# 3. seed 唯一账号 + 默认配置
python scripts/init_db.py
# ADMIN_PASSWORD 只用于本步骤；seed 完成后可从运行时环境中移除

# 4. 启动后端
cd backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 5. 启动前端（开发模式）
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173

# 6. 验证后端 API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<ADMIN_PASSWORD>"}' -c /tmp/c.txt
curl http://localhost:8000/api/auth/me -b /tmp/c.txt

# 7. 生产构建前端
cd frontend
npm run build          # 输出到 frontend/dist/
```

## 配置说明

核心配置在 `backend/config/default.json`，运行时可通过 `system_config` 表覆盖：

- `sources.buckets`：两个桶（venue + arxiv），各自 `enabled`/`quota`/`include_venue_hint`
- `sources.fill_policy`：`strict`（宁缺毋滥）或 `spillover`（跨桶补足）
- `llm.daily_budget`：每日 LLM 费用上限（USD），超额降级为预筛排序
- `scheduler.digest_cron`：默认 `"0 9 * * *"`（每天09:00发送）

## 数据库

6 张表：`users`（单行）、`papers`、`tags`（反馈）、`keywords`、`digest_history`、`system_config`。

迁移：`cd backend && alembic upgrade head`。初始化账号和默认 `system_config`：`python scripts/init_db.py`。

## 分阶段进度

| Phase | 内容 | 状态 |
|-------|------|------|
| 0 | 环境准备（MySQL / mTLS 证书 / DNS） | ⬜ 手动 |
| 1 | 后端骨架（认证 + 数据库） | ✅ |
| 2 | arXiv 抓取 + 去重入库 | ✅ |
| 3 | 评分管线（关键词 + 分桶 + 预筛） | ✅ |
| 4 | LLM 集成（批量打分 + 成本控制） | ✅ |
| 5 | 邮件通知 + 反馈链接 | ✅ |
| 6 | 前端（Vue 3 + Naive UI） | ✅ |
| 7 | 部署上线（Nginx mTLS + APScheduler） | ⬜ |

## 前端补充说明

- 当前主视觉已经统一到偏 Linear 的研究工作台风格，重点服务 AI researcher 的“扫读论文 -> 标记反馈 -> 调整订阅”流程。
- 已完成统一收口的页面：`/login`、`/dashboard`、`/digest`、`/papers`、`/keywords`、`/settings`。
- 下一步前端重点不是继续堆页面，而是提升阅读流与设置流的效率：优先改 `PaperDetail`、`Digest`、筛选体验和前端自动化验收。

## 参考文档

- `paper-digest-plan.md` — 落地计划（施工蓝图，含验收标准）
- `../archive/` — 历史设计方案（v1 CLI / v2 Python+JSONL / v3 全栈）
