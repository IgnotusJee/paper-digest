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
- 前端：Vue 3 + Naive UI + TypeScript + Vite
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
│               └── sources.py  # Phase 6+
└── frontend/                   # Vue 3（Phase 6）
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

# 4. 启动
cd ..
docker compose up -d

# 5. 验证
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<ADMIN_PASSWORD>"}' -c /tmp/c.txt
curl http://localhost:8000/api/auth/me -b /tmp/c.txt
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
| 2 | arXiv 抓取 + 去重入库 | ⬜ |
| 3 | 评分管线（关键词 + 分桶 + 预筛） | ⬜ |
| 4 | LLM 集成（批量打分 + 成本控制） | ⬜ |
| 5 | 邮件通知 + 反馈链接 | ⬜ |
| 6 | 前端（Vue 3 + Naive UI） | ⬜ |
| 7 | 部署上线（Nginx mTLS + APScheduler） | ⬜ |

## 参考文档

- `../paper-digest-plan.md` — 落地计划（施工蓝图，含验收标准）
- `../archive/` — 历史设计方案（v1 CLI / v2 Python+JSONL / v3 全栈）
