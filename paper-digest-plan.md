# AI 论文日报系统 — 落地计划（v3.1 单文件版）

> 本文是施工蓝图。设计依据与各项决策的论证见 `paper-digest-v3.1.md`（审计修订版），本文只讲"做什么、怎么做、做到什么程度算完成"。

---

## 1. 项目目标

每天自动从顶刊顶会与 arXiv 发现 LLM 存储/推理/AI 基础设施方向的优秀论文，AI 打分排序、中文翻译总结，按来源配额混合后通过邮件推送；提供一个公网可访问、仅本人设备能登录的 Web 控制面板，用于浏览、反馈、调关键词与来源配额。反馈驱动推荐逐步个性化。

**核心约束（来自用户）：**

- 单用户，但要认证，且公网直连下只有本人设备能登录。
- 每天推荐按来源配额混合：几篇顶刊顶会 + 几篇 arXiv，比例与每个来源是否启用均可开关。
- 复用现成 VPS 与现成 MySQL 容器，Web 前端常驻。
- 通知首期只做 Email。
- LLM 成本可控，低成本运行。

---

## 2. 系统架构

```
                          公网
                           │  HTTPS 443 (mTLS：仅本人设备证书可握手)
                           ▼
                  ┌─────────────────┐
                  │  Nginx          │  客户端证书校验 + 静态前端 + API 反代
                  └───────┬─────────┘
                          │ 内网 8000
                          ▼
        ┌──────────────────────────────────────────┐
        │  FastAPI 后端 (Uvicorn)                    │
        │  ┌──────────┐ ┌──────────┐ ┌───────────┐ │
        │  │ Auth     │ │ Papers/  │ │ Settings/ │ │
        │  │ cookie   │ │ Digest/  │ │ Keywords/ │ │
        │  │ 会话+限流│ │ Feedback │ │ Sources   │ │
        │  └──────────┘ └──────────┘ └───────────┘ │
        │  ┌────────────────────────────────────┐  │
        │  │ APScheduler 定时引擎                │  │
        │  │  抓取 → 分桶预筛 → LLM重排 → 发邮件 │  │
        │  └────────────────────────────────────┘  │
        │  core: fetcher / dedup / scorer /         │
        │        recommender / pipeline / llm_client│
        │  notifier: email                          │
        └───────┬───────────────┬──────────────┬────┘
                │               │              │
                ▼               ▼              ▼
        ┌────────────┐  ┌──────────────┐  ┌──────────────────┐
        │ 现成 MySQL │  │ LLM API      │  │ arXiv / DBLP / S2 │
        │ (独立库)   │  │ DeepSeek/Kimi│  │ 论文数据源        │
        └────────────┘  └──────────────┘  └──────────────────┘
                │
                ▼
        本地卷: SVM/质心模型文件 (models/)
```

---

## 3. 技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| 后端 | FastAPI + Uvicorn | async，自带 OpenAPI |
| ORM | SQLAlchemy 2.0 (async) + asyncmy | MySQL async 驱动 |
| 数据库 | 复用 VPS 现成 MySQL，建独立库 `paper_digest` | utf8mb4 |
| 定时 | APScheduler（内嵌 backend 进程） | cron 触发 |
| 认证 | argon2id 密码哈希 + JWT(httpOnly cookie) | 无注册端点 |
| 访问控制 | Nginx mTLS 客户端证书 + 登录限流 + 可选 IP 白名单 | 设备级白名单 |
| 推荐 | TF-IDF 质心 / 校准 LogisticRegression | 三段门控 |
| LLM | DeepSeek → Kimi（fallback，带预算闸/熔断） | OpenAI 兼容 |
| 邮件 | aiosmtplib + Jinja2 | 异步 SMTP |
| 前端 | Vue 3 + Naive UI + TypeScript + Vite + Pinia | 中文友好 |
| 反代 | Nginx | TLS 终止 + mTLS |
| 部署 | Docker Compose（backend + nginx，复用现成 MySQL） | 2 容器 |

---

## 4. 核心设计决策

每条给出"决策 + 一句话理由"，详尽论证见审计文档对应章节。

### 4.1 认证与访问控制

- **无注册端点**：账号在 `init_db` 时从环境变量 seed 出唯一一个，之后无任何注册入口。理由：单用户，开放注册是反向设计。
- **httpOnly + Secure + SameSite=strict cookie 承载 JWT**：而非 localStorage。理由：防 XSS 窃取 token、防 CSRF。
- **mTLS 客户端证书做设备白名单**：自建 CA 只给本人设备签证书，Nginx `ssl_verify_client on`，无证书的设备 TLS 握手即被拒。理由：MAC 在公网不可见无法过滤；mTLS 是密码学级、可公网验证的设备绑定。
- **登录限流**：内存滑动窗口，5 次/5 分钟/IP。理由：防爆破，单进程无需 Redis。
- **可选 IP 白名单**：出口 IP 固定时在 Nginx 叠加，作纵深防御。
- **补强项（落地时一并加）**：HSTS 强制 HTTPS、CSRF token、登录与敏感操作审计日志、JWT_SECRET 定期轮换。

### 4.2 推荐算法（第二级个性化，三段门控）

按累计反馈量自动切换模式，全程以 `paper_id` 为锚，绝不依赖临时行号：

| 模式 | 触发条件 | 算法 | 输出 |
|---|---|---|---|
| `off` | 正样本 < 1 | 不个性化 | 0.5（其权重并入 keyword） |
| `centroid` | 1 ≤ 正样本 < 20 | TF-IDF 正样本质心余弦相似度 | 余弦 ∈ [0,1] |
| `model` | 正、负样本均 ≥ 20 | CalibratedClassifierCV(LogisticRegression) | 校准后正类概率 |

- 理由：稀疏反馈下直接训 SVM 必过拟合；质心相似度无可学坏的参数、有 1 条正样本即可用，补冷启动空窗；LR+校准给出可与其他分加权的真实概率；paper_id 锚定消除"语料重建→行号漂移"的 bug。
- **重训时机**：事件触发——新增标记置脏标志，当日生成前若脏则重训一次，否则复用。

### 4.3 评分管线（分桶配额 + 召回/排序分离）

```
第0步 分桶：候选按来源归入 venue 桶 / arxiv 桶（各有 enabled 开关与 quota）
第A步 桶内预筛：每桶内算 prefilter_score 排序，取 quota×oversample(默认3) 篇
        prefilter_score = 0.45*keyword + 0.30*personal + 0.15*recency + 0.10*source_prior
        （personal=off 时其 0.30 权重并入 keyword，不掺 0.5）
        各桶候选合并为 shortlist
第B步 LLM 重排 + 配额回填：对 shortlist 批量打分(relevance 0~10)；
        每个桶内按 LLM 分降序各取 quota 篇 → 当日 = venue配额 + arxiv配额
        供给不足时按 fill_policy：strict(宁缺毋滥) 或 spillover(其他桶补足)
        LLM 熔断时桶内改用 prefilter 序，并标注"未经 LLM 精排"
```

- 理由：配额决定"每个来源拿几篇"，LLM 分决定"该来源里拿哪几篇"，二者正交，满足"按比例混合来源"且不为凑配额塞低质论文。没进 LLM 的论文不参与最终排序，消除 v3 用 0.5 填充缺失 LLM 分的污染。
- **引用数不进排序**：S2 限流不可靠且新论文引用近 0；改离线富集，只在详情页展示。

### 4.4 数据源（三来源喂两桶）

- **arXiv 日更**：按 cs.DC/cs.AR/cs.OS/cs.PF/cs.LG/cs.AI + 关键词查询，每日增量，`venue=None, source='arxiv'`。每日新鲜流的唯一真实来源。
- **DBLP/proceedings 批量**：一年几次按会议+年份导入，`venue` 有值，`source='dblp'`；见刊时与已有 arXiv 预印本跨源去重合并。
- **venue_hint 指向标注**：对 arXiv 论文从 comments 提取作者自报的录用信息（"Accepted to OSDI'25"），打 `venue_hint`。理由：顶会一年才发一次，要"每天推顶会"必须在预印本阶段识别会议指向，否则 venue 桶常空。
- **归桶规则**：已见刊(`venue`命中) 或 带可信指向(`venue_hint`命中，可开关) → venue 桶；纯预印本 → arxiv 桶。
- **source_prior**（桶内预筛轻微加权）：已见刊 1.0 > 有指向 0.8 > 纯预印本 0.6。
- **诚实标注**：UI 区分"已见刊 FAST 2025"与"指向 OSDI'25（预印本）"，不把弱信号伪装成已见刊。

### 4.5 去重（三级 + 跨源合并）

匹配顺序：`doi` → `arxiv_id` → 归一化标题 hash（小写、去标点、压空格的 SHA256[:16]），任一命中即同篇。合并时优先保留有 venue/doi 的权威信息，保留 `pushed` 状态避免二次推送。理由：同篇论文 arXiv 版与正式版标题措辞常不同。

### 4.6 LLM 集成（成本可控）

- **fallback 链只放便宜模型**：DeepSeek → Kimi。OpenAI/Claude 不进默认链，要用须显式配置。理由：杜绝静默降级到贵模型致费用暴涨。
- **三道成本闸**：单次成本上限 `MAX_COST_PER_CALL`；每日预算 `DAILY_BUDGET`，超额当天停用 LLM 降级为预筛序；`cost_tracker` 写 MySQL 持久化，重启不清零。
- **熔断器**：供应商连续失败 N 次进冷却期，跳过不重试，冷却后半开重试。
- **JSON schema 校验 + 一次截断修复**：坏 JSON 不致整次日报崩溃。
- **批量大小** ~12–15 篇/次，降低 token 量与截断概率。

### 4.7 通知（仅 Email）

- 只实现 EmailNotifier（保留 BaseNotifier 抽象供将来扩展）。
- **反馈走网页而非邮件按钮**：邮件每篇带指向详情页的链接，链接含 HMAC 短时效签名 token（绑 paper_id+动作+过期），点击落到已登录面板执行。理由：网页反馈直接带 paper_id，绕开 v3 中"IM 回调 idx→paper_id"未接好的链路；token 过期即失效，邮件被转发也安全。

---

## 5. 数据模型（MySQL，SQLAlchemy 2.0）

`class Base(DeclarativeBase)`，字段用 `Mapped[...] + mapped_column(...)`。下表为逻辑结构，类型按 MySQL 适配。

**users**（单行）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INT PK | |
| username | VARCHAR(64) UNIQUE | |
| email | VARCHAR(128) | 收件地址 |
| hashed_password | VARCHAR(256) | argon2id |
| is_active | BOOL | |
| notify_email | BOOL | 邮件开关 |
| daily_total | INT | 每日推荐总篇数（默认 6） |
| created_at | DATETIME | |

**papers**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INT PK | |
| title | TEXT | |
| title_hash | VARCHAR(16) UNIQUE IDX | 去重 |
| authors | JSON | |
| venue | VARCHAR(32) IDX NULL | 已正式见刊才填 |
| venue_hint | VARCHAR(32) IDX NULL | 预印本会议指向 |
| year | INT | |
| abstract_en | LONGTEXT | |
| abstract_cn | LONGTEXT | LLM 翻译 |
| summary_cn | JSON | {核心问题,创新点,关键方法,实验亮点,推荐理由} |
| comments | TEXT NULL | arXiv comments 原文（提 venue_hint 用） |
| url / pdf_url | TEXT | |
| arxiv_id | VARCHAR(32) IDX NULL | |
| doi | VARCHAR(128) IDX NULL | |
| citation_count | INT | 离线富集，仅展示 |
| source | VARCHAR(16) | arxiv / dblp / manual |
| keyword_score / personal_score / prefilter_score / llm_score / final_score | FLOAT | |
| llm_reason | TEXT | |
| bucket | VARCHAR(16) NULL | 本次归桶 venue/arxiv |
| pushed | BOOL IDX | |
| pushed_at | DATETIME NULL | |
| created_at | DATETIME | |

**tags**（反馈，驱动推荐）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INT PK | |
| paper_id | INT FK IDX | |
| tag_type | VARCHAR(16) | interested / not_interested / read_later |
| created_at | DATETIME | |

**keywords**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INT PK | |
| keyword | VARCHAR(128) UNIQUE | |
| weight | FLOAT | 正=感兴趣，负=排斥 |
| category | VARCHAR(32) | topic/method/system |
| aliases | JSON | 别名列表 |
| source | VARCHAR(16) | manual/feedback/preset |
| updated_at | DATETIME | |

**digest_history**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INT PK | |
| digest_date | DATE IDX | |
| paper_ids | JSON | 当日推送的论文 |
| bucket_breakdown | JSON | {venue:[...], arxiv:[...]} 配额实际产出 |
| channel | VARCHAR(16) | email |
| status | VARCHAR(16) | sent / failed / degraded |
| created_at | DATETIME | |

**system_config**（含 LLM 成本累计）

| 字段 | 类型 | 说明 |
|---|---|---|
| key | VARCHAR(64) PK | 如 `cost:2026-06-17` |
| value | TEXT | |
| updated_at | DATETIME | |

---

## 6. 配置（`config/default.json`，运行时部分可由面板改写入 system_config）

```json
{
  "sources": {
    "daily_total": 6,
    "fill_policy": "strict",
    "oversample": 3,
    "buckets": [
      {"name": "venue", "enabled": true, "quota": 3,
       "venues": ["FAST","OSDI","SOSP","ISCA","ASPLOS","EuroSys","ATC","NSDI","SC","VLDB","SIGMOD"],
       "include_dblp": true, "include_venue_hint": true},
      {"name": "arxiv", "enabled": true, "quota": 3,
       "arxiv_categories": ["cs.DC","cs.AR","cs.OS","cs.PF","cs.LG","cs.AI"]}
    ]
  },
  "scoring": {
    "prefilter": {"keyword": 0.45, "personal": 0.30, "recency": 0.15, "source_prior": 0.10}
  },
  "recommender": {"min_pos_centroid": 1, "min_pos_model": 20, "min_neg_model": 20},
  "llm": {
    "chain": ["deepseek", "kimi"],
    "daily_budget": 0.50,
    "max_cost_per_call": 0.10,
    "batch_size": 12,
    "circuit_threshold": 3,
    "circuit_cooldown_sec": 600
  },
  "scheduler": {"digest_cron": "0 9 * * *", "fetch_cron": "30 */6 * * *"}
}
```

---

## 7. 目录结构

```
paper-digest/
├── docker-compose.yml          # backend + nginx（连现成 MySQL external network）
├── Dockerfile.backend
├── nginx.conf                  # 443 mTLS + 静态前端 + API 反代
├── certs/                      # server.crt/key + ca.crt（客户端 CA）
├── .env                        # 密钥与 DB 连接（不入库）
│
├── backend/
│   ├── requirements.txt
│   ├── alembic/                # 迁移
│   ├── config/
│   │   ├── default.json
│   │   └── presets/            # 关键词预设包
│   ├── prompts/
│   │   ├── batch_score.txt
│   │   ├── batch_translate.txt
│   │   └── extract_keywords.txt
│   ├── templates/email.html
│   ├── models/                 # 质心/LR 模型文件（卷持久化）
│   ├── scripts/
│   │   ├── init_db.py          # seed 唯一账号 + 默认配置（建表由 Alembic 负责）
│   │   ├── seed_keywords.py
│   │   └── gen_client_cert.sh  # 自建 CA + 签设备证书
│   └── src/
│       ├── main.py  config.py  database.py  models.py  auth.py
│       ├── api/routes/{auth,papers,digest,feedback,keywords,settings,sources}.py
│       ├── api/deps.py
│       ├── core/{fetcher,dedup,scorer,recommender,pipeline,llm_client}.py
│       ├── notifier/{base,email_notifier}.py
│       └── scheduler.py
│
└── frontend/
    ├── package.json  vite.config.ts  tsconfig.json
    └── src/
        ├── main.ts  App.vue  router/index.ts
        ├── stores/{auth,papers}.ts
        ├── api/{client,auth,papers,settings}.ts
        ├── views/{Login,Dashboard,Papers,PaperDetail,Digest,Keywords,Settings,Sources}.vue
        └── components/{PaperCard,ScoreBar,SourceQuotaEditor,KeywordTable}.vue
```

---

## 8. 分阶段落地流程

每个阶段按序进行，通过验收后再进入下一阶段。

---

### Phase 0 — 环境准备（无代码，约 0.5 天）

**目标**：基础设施就绪，后续不因环境返工。

**任务清单：**

- [ ] MySQL 建独立库与用户（不动现有数据）：
  ```sql
  CREATE DATABASE paper_digest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER 'pd_user'@'%' IDENTIFIED BY '<DB_PASS>';
  GRANT ALL PRIVILEGES ON paper_digest.* TO 'pd_user'@'%';
  ```
- [ ] 记录现有 MySQL 容器所在 Docker 网络名（`docker network ls`）。
- [ ] 生成 mTLS 证书（`scripts/gen_client_cert.sh`）：
  - 自建 CA（10 年有效期）→ `certs/ca.crt + ca.key`
  - 服务端证书用 Let's Encrypt（certbot）：`certbot certonly --standalone -d paper.yourdomain.com`，证书路径 `/etc/letsencrypt/live/paper.yourdomain.com/`；Nginx 引用该路径（需挂载进容器）
  - 给本人设备签客户端证书 → `certs/client_laptop.p12`
  - 将 `.p12` 导入 macOS 钥匙串 / Chrome 证书管理
- [ ] 填写 `.env`（JWT_SECRET 用 `openssl rand -hex 32`；不入 git）。
- [ ] 域名 DNS A 记录指向 VPS（Let's Encrypt 需要）。

**验收**：`mysql -u pd_user -p paper_digest` 可连通；`.p12` 导入浏览器无报错。

---

### Phase 1 — 后端骨架（认证 + 数据库，约 1.5 天）

**目标**：FastAPI 服务可跑，单账号认证通，所有表建好。

**依赖**：Phase 0。

**任务清单：**

- [x] `requirements.txt`：fastapi, uvicorn, sqlalchemy>=2.0, asyncmy, alembic, passlib[argon2], python-jose[cryptography], aiosmtplib, scikit-learn, joblib, httpx, apscheduler, jinja2, python-multipart
- [x] `src/models.py`：按第 5 节建所有 ORM 模型（SQLAlchemy 2.0 `Mapped` 风格，utf8mb4）
- [x] `src/database.py`：async 引擎 + sessionmaker，`pool_pre_ping=True`
- [x] Alembic 初始化 → `alembic upgrade head` 建表
- [x] `scripts/init_db.py`：seed 唯一账号（argon2id），已存在则跳过；写入默认 system_config
- [x] `src/auth.py`：argon2id 密码校验 + JWT 签发/验证（12h 有效期）
- [x] `src/api/routes/auth.py`：
  - `POST /api/auth/login`：校验 + 登录限流（内存滑动窗口 5次/5min/IP）+ set httpOnly Secure SameSite=strict cookie
  - `POST /api/auth/logout`：delete cookie
  - `GET /api/auth/me`：验证 cookie 返回用户信息
  - **无 /register，无 /refresh**
- [x] `src/api/deps.py`：`get_current_user` 从 cookie 解 JWT，失败 → 401
- [x] `src/main.py`：挂 auth 路由，`GET /health`，CORS 仅同源
- [x] `Dockerfile.backend` + `docker-compose.yml`（Phase 1：backend 暴露 8000 调试用）

**验收标准**：
- `GET /health` → 200
- 正确密码登录 → 200 + Set-Cookie
- 错误密码 ×6 → 429
- 有效 cookie `GET /api/auth/me` → 200
- 无 cookie → 401
- MySQL `SHOW TABLES` 列出所有模型表

---

### Phase 2 — 数据采集（arXiv 抓取 + 去重入库，约 1.5 天）

**目标**：每天能自动抓 arXiv 增量入库，venue_hint 识别，三级去重正确合并。

**依赖**：Phase 1。

**任务清单：**

- [x] `src/core/fetcher.py`：
  - `fetch_arxiv(categories, date) → list[PaperRaw]`：调 arXiv API（`http://export.arxiv.org/api/query`），按类目 + 日期过滤，提取 title/authors/abstract/arxiv_id/pdf_url/comments
  - 速率：每次请求间隔 3s（arXiv 要求）
- [x] `src/core/dedup.py`：
  - `norm_title(t)` → 小写、去标点、压空格
  - `title_hash(t)` → SHA256[:16]
  - `find_duplicate(paper, db)` → 三级查询 doi → arxiv_id → title_hash
  - `merge_into(existing, incoming)` → 补 venue/doi，保留 pushed 状态
- [x] `src/core/venue_hint.py`：
  - 正则扫 arXiv comments 字段，匹配 "Accepted/to appear at OSDI'25" 等模式，返回 venue 名称或 None
  - 支持在 `config.sources.buckets[0].venues` 列表里匹配
- [x] `src/core/pipeline.py` 中 `run_fetch_job()`：fetch → venue_hint → dedup → upsert DB
- [x] 手动触发脚本 `scripts/run_fetch.py` 用于测试
- [x] `GET /api/papers`（分页+排序）+ `GET /api/papers/{id}`：供后续验证入库结果

**进度记录（2026-06-17）**：
- 已补 Phase 2 的生产正确性修复：arXiv comments/DOI 按 `arxiv:` 扩展命名空间解析；API 查询包含 `submittedDate` 日期范围；跨源合并时已有 `venue`/`venue_hint` 的记录保持或升级到 venue 桶；upsert 异常统一计入 `errors`。
- 已增加回归测试覆盖上述路径。已解决本机 sandbox/WSL/conda 环境下 `aiosqlite` worker 线程回调无法唤醒事件循环的问题，完整后端测试可跑通。

**验收标准**：
- 运行 `run_fetch.py` 后 papers 表有新记录
- 同一篇论文重复抓取后表中仍只有一条记录
- `venue_hint` 字段对 comments 含 "Accepted at SOSP" 的论文正确填值
- 跨源合并：手动插入一条有 arxiv_id 的 dblp 记录，再抓同 arxiv_id 的 arXiv 版，应合并为一条且 venue 补上

---

### Phase 3 — 评分管线（关键词 + 分桶 + 预筛，约 1 天）

**目标**：候选论文能按来源正确分桶，桶内预筛打分，生成送 LLM 的 shortlist。

**依赖**：Phase 2。

**任务清单：**

- [x] `src/core/scorer.py`：
  - `keyword_match(paper, keywords) → float [0,1]`：主词 + aliases 加权匹配，归一化
  - `recency_score(paper) → float [0,1]`：时间指数衰减（7 天半衰期）
  - `source_prior(paper) → float`：venue=1.0 / venue_hint=0.8 / arxiv=0.6
  - `prefilter_score(paper, keyword, personal, has_personal) → float`：加权组合
- [x] `src/core/pipeline.py` 中 `assign_bucket(paper, cfg)` + 桶内预筛逻辑
- [x] `src/core/recommender.py`：按第 4.2 节实现三段门控（off/centroid/model），paper_id 锚定
- [x] `GET /api/keywords` + `POST/PUT/DELETE /api/keywords` + `POST /api/keywords/preset`（加载预设包）
- [x] 加载初始关键词 `scripts/seed_keywords.py`

**验收标准**：
- 有关键词配置的情况下，100 篇候选按 keyword_score 排序结果符合预期（人工检查前 10）
- `assign_bucket` 对 venue='FAST' 的论文归入 venue 桶，对纯 arXiv 归入 arxiv 桶，对 venue_hint='OSDI' 且 include_venue_hint=true 也归入 venue 桶
- venue 桶 quota=3，arxiv 桶 quota=3，oversample=3 时 shortlist 长度 ≤ 18
- recommender `mode='off'` 时 `score()` 返回 0.5；给 3 条 paper_id 标 interested 后 mode 变 `centroid`，score 不再是 0.5

---

### Phase 4 — LLM 集成（批量打分 + 成本控制，约 1 天）

**目标**：shortlist 能经 LLM 打分，有预算闸/熔断/JSON 校验，降级路径可用。

**依赖**：Phase 3。

**任务清单：**

- [x] `src/core/llm_client.py`：按第 4.6 节实现：
  - `LLMChain`：DeepSeek → Kimi，单次成本上限，日预算闸（读 system_config `cost:DATE`）
  - `CircuitBreaker`：连续失败 N 次 → 冷却期，冷却后半开
  - `chat_json(messages)` + `_parse_or_retry(raw)`：JSON 截断修复 + schema 校验
- [x] `src/core/pipeline.py` 中 `run_llm_rank(shortlist)` → 桶内按 LLM 分取配额 → 处理 fill_policy
- [x] `prompts/batch_score.txt`：提示词，要求返回 `{"papers": [{"id":..., "relevance":0-10, "reason":"..."}]}`
- [x] `prompts/batch_translate.txt`：对最终 6 篇批量翻译 + 生成 summary_cn 结构
- [x] `system_config` cost 记录写入与读取
- [x] `GET /api/settings` + `PUT /api/settings`（含 LLM 配置，面板可改 daily_budget）

**进度记录（2026-06-18）**：
- 已完成 Phase 4 的审计回归修复：`/api/settings` 现执行严格配置校验并仅负责保存；`run_scoring_job()` 改为每次重算全部论文的 `keyword_score/personal_score/prefilter_score/bucket`；LLM 在收到 200 响应且提供 usage 时，会先记账再做 JSON/schema/validator 校验，因此 malformed-but-200 响应也会计入当日成本。
- 已补充 LLM 计费、LLM 降级、settings 校验、全量 rescoring 的回归测试，完整后端测试当前通过。

**验收标准**：
- 给 12 篇测试论文调 LLM，返回正确 JSON，papers 表 llm_score 有值
- 手动把 daily_budget 设为 ¥0.001，再调 LLM → 抛 `LLMUnavailable`，pipeline 降级为 prefilter 序
- 手动触发供应商 API Key 错误（改错 key），连续 3 次失败后该供应商进熔断，第 4 次直接跳过不重试
- LLM 返回 JSON 前后加多余文字时，`_parse_or_retry` 能修复并返回正确数据

---

### Phase 5 — 邮件通知 + 反馈链接（约 1 天）

**目标**：完整的每日 digest 流程跑通：pipeline → 发邮件 → 点链接回面板反馈。

**依赖**：Phase 4。

**任务清单：**

- [ ] `src/notifier/email_notifier.py`：aiosmtplib + Jinja2 模板，`send_digest(user, papers)`
- [ ] `templates/email.html`：每篇论文展示 title_cn、venue/venue_hint 标注、summary_cn 各字段、PDF 链接、「查看/反馈」按钮（指向 `BASE_URL/papers/{id}`）
- [x] **反馈 token**：`src/auth.py` 中 `gen_feedback_token(paper_id, action, ttl=72h)` + `verify_feedback_token(token)`（HMAC-SHA256，绑 paper_id+action+exp）
- [ ] `GET /api/papers/{id}/feedback?token=...&action=interested`：验证 token → 若已登录直接写 Tag；若未登录重定向登录页（登录后跳回）
- [ ] `POST /api/papers/{id}/tag` + `DELETE /api/papers/{id}/tag`：已登录用户的直接反馈
- [ ] `GET /api/digest` + `GET /api/digest/{date}`：返回当日/历史推荐
- [ ] 手动触发脚本 `scripts/run_digest.py`（测试单次完整 pipeline）

**验收标准**：
- 运行 `run_digest.py`：papers 表最终 6 篇 `pushed=True`，digest_history 有一条记录
- 收到邮件，HTML 格式正常，venue/venue_hint 分别标"已见刊"/"录用指向"，中文摘要各字段完整
- 点邮件中的「查看/反馈」链接：未登录时跳登录页，登录后正确落到论文详情
- 点 token 链接反馈 interested → tags 表有记录，且同一 token 第二次点失效（token 已使用或过期）
- 手动标记 21 条 interested + 21 条 not_interested → recommender mode 变为 `model`

---

### Phase 6 — 前端（最小可用 Web 面板，约 2 天）

**目标**：浏览器可登录、看今日推荐、给论文标记反馈、管理关键词和来源配额。

**依赖**：Phase 5（API 已就绪）。

**页面清单（按优先级）**：

| 优先 | 路由 | 功能 |
|---|---|---|
| P0 | `/login` | 登录，失败提示，429 友好提示 |
| P0 | `/digest` | 今日推荐，按来源分组（顶会 / arXiv），每篇展示 title_cn、venue 标注、summary 摘要、「感兴趣/不感兴趣/稍后」按钮 |
| P0 | `/papers/:id` | 论文详情：中英文摘要、结构化分析、分数详情、反馈按钮 |
| P1 | `/keywords` | 关键词表（增删改权重、加载预设） |
| P1 | `/settings/sources` | 来源配额开关：两个桶的 enabled toggle + quota 滑块 + fill_policy 选择 |
| P2 | `/dashboard` | 统计卡片（今日推荐数、已推总数、标记数、recommender 当前模式） |
| P2 | `/papers` | 论文列表（分页、按来源/日期/分数过滤） |
| P2 | `/digest/:date` | 历史某天推荐 |
| P2 | `/settings` | LLM 预算、SMTP 测试、定时任务下次运行时间 |

**技术要点**：

- `api/client.ts`：Axios 实例，`withCredentials:true`（cookie 自动携带），401 拦截跳登录页
- 路由守卫：未登录访问任意路由 → 跳 `/login`，登录后跳回原路由
- `/settings/sources`：`SourceQuotaEditor` 组件，修改后 `PUT /api/settings/sources` 即时生效（写入 system_config）

**验收标准**：
- 无客户端证书的浏览器访问 443 → Nginx 400（TLS 握手失败，此阶段配好 Nginx mTLS）
- 有证书的浏览器可正常登录
- 今日推荐页展示 6 篇，venue 桶与 arxiv 桶分组正确
- 点「感兴趣」→ 按钮状态变更，刷新后保持
- 关键词页增删可用，`POST /api/keywords/preset` 加载预设包
- 来源配额改 quota → 次日推送比例变化（或手动触发验证）

---

### Phase 7 — 部署上线（Nginx mTLS + APScheduler + Docker 完整启动，约 0.5 天）

**目标**：生产环境两容器常驻运行，mTLS 正式上线，定时任务每天自动执行。

**依赖**：Phase 6。

**任务清单：**

- [ ] `nginx.conf`：443 终止 TLS，`ssl_verify_client on`，`ssl_client_certificate certs/ca.crt`，代理 `/api/` 到 backend，`/` 服务 Vue dist
- [ ] 更新 `docker-compose.yml`：backend 改为 `expose: [8000]`（不映射宿主），nginx 映射 443，挂 certs 卷，external network 连 MySQL
- [ ] Vue 生产构建在 `Dockerfile.frontend`（多阶段构建：Node 阶段 `npm run build`，产物复制进 nginx 容器的 `/usr/share/nginx/html`；backend 用独立 `Dockerfile.backend`）
- [ ] `src/scheduler.py`：APScheduler 注册两个 cron：
  - `fetch_papers_job`：每 6 小时增量抓取
  - `daily_digest_job`：每天 09:00 完整 pipeline（fetch → score → LLM → email）
- [ ] `src/main.py` 中 `lifespan` 启动/关闭 scheduler
- [ ] 测试：`docker compose up -d`，观察 `docker compose logs -f backend` 确认 scheduler 启动
- [ ] 手动触发 `daily_digest_job` 一次：`POST /api/settings/trigger-digest`（保留；需携带有效 cookie 才能访问，防止公网任意触发）

**验收标准**：
- 无客户端证书的浏览器访问 `https://paper.yourdomain.com` → 400 Bad Request（TLS 握手失败）
- 安装证书的浏览器正常访问面板
- `docker compose ps` 两个容器均为 Up
- 次日 09:00 自动收到邮件（或手动触发后立即收到）
- 重启 `docker compose restart backend` 后 scheduler 重新启动、日预算不清零（从 DB 读取）

---

### Phase 8 — 后期增强（攒够数据后迭代，无硬截止）

以下功能等运行一段时间、数据积累后再做，不阻塞上线：

| 功能 | 触发条件 | 说明 |
|---|---|---|
| recommender 升级到 `model` 模式 | 累计 interested ≥ 20 且 not_interested ≥ 20 | 门控自动切，无需代码改动 |
| DBLP/proceedings 批量导入 | 每年顶会放榜后 | `scripts/import_proceedings.py`，触发跨源合并 |
| S2 引用数离线富集 | 数据库积累到 1000+ 篇时 | batch API，只进详情页展示 |
| Telegram 通知 | 解决服务器网络问题后 | 在 `BaseNotifier` 抽象上新增实现，不影响现有 |
| 关键词自动演化 | 邮件/面板反馈足够多后 | LLM 从标记论文提取关键词，写入 Keyword 表 |

---

## 9. 风险与未决事项

| 风险 | 可能性 | 应对 |
|---|---|---|
| arXiv comments 格式多样，venue_hint 提取遗漏 | 中 | 正则漏匹配时 venue 桶当天可能为空（fill_policy=strict 不补位）；可后期手动补 venue_hint 字段，或在面板直接移桶 |
| VPS MySQL 容器网络名变更或重建 | 低 | external network 名写入 .env，变更时只改一处 |
| DeepSeek/Kimi API 同时不可用 | 低 | 两者均熔断后降级为预筛排序，邮件标注"未经 LLM 精排"，不中断发送 |
| arXiv API 返回格式变化 | 低 | fetcher 层封装，改一处；用原始 XML 存 comments 字段备查 |
| 客户端证书在某些设备/浏览器上配置复杂 | 中 | .p12 导入 macOS 钥匙串最简单；Firefox 需在证书管理器里单独导入 |
| MySQL 连接池满（高频并发） | 极低（单用户） | 默认池大小够用；出现时调 `pool_size` |

**已确定决策**（所有设计选项均已确认，无待定项）：

1. **服务端证书**：Let's Encrypt（certbot），详见 Phase 0。
2. **`fill_policy`**：`strict`——venue 桶供给不足时宁缺毋滥，不让 arXiv 补位，当日推送可少于 `daily_total`。
3. **`venue_hint` 默认启用**：`include_venue_hint: true`；arXiv 预印本自报录用信息归入 venue 桶，UI 与邮件中标注区分"已见刊"与"录用指向（预印本）"。
4. **前端构建**：Dockerfile 多阶段构建（Node 阶段 build，产物进 nginx 容器），不依赖宿主 Node 环境。
5. **`/api/settings/trigger-digest` 保留**：受 cookie 鉴权保护，仅本人已登录状态可调。
