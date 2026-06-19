# Frontend

前端是一个面向 AI researcher 的研究阅读面板，负责登录、查看每日 digest、浏览论文库、维护关键词和系统配置。

## 当前状态

已完成的页面与交互：

- `/login`：双栏登录页，本地开发通过 Vite 代理访问后端
- `/dashboard`：研究工作台首页，展示今日推荐与快捷入口
- `/digest`：按 `venue / arxiv` 分桶浏览当日推荐
- `/papers`：论文库，支持来源与排序筛选
- `/papers/:id`：论文详情页
- `/keywords`：关键词表，支持增删改与加载预设
- `/settings`：来源配额、LLM 预算、调度配置

当前视觉语言已经统一到一套偏 Linear 的研究工具风格：

- 冷静中性色背景
- 单一蓝色强调色
- 12px 左右的统一圆角体系
- 页面标题、控制面板、数据卡片使用一致层级
- 避免紫色 AI 渐变和泛化营销感组件

## 技术结构

- `src/App.vue`：Naive UI 全局主题
- `src/router/index.ts`：路由与登录守卫
- `src/stores/auth.ts`：登录态管理
- `src/api/`：按资源拆分的 API 封装
- `src/components/AppLayout.vue`：主框架、侧边栏、顶部栏
- `src/components/PageHeader.vue`：统一页头
- `src/components/PaperCard.vue`：论文卡片
- `src/components/SourceQuotaEditor.vue`：来源配额编辑器
- `src/views/`：页面视图

## 本地开发

前端默认通过 Vite 代理把 `/api` 转发到 `http://localhost:8000`。

```bash
cd frontend
npm install
npm run dev
```

默认开发地址：

- `http://127.0.0.1:4173/` 或 Vite 输出的本地地址

生产构建：

```bash
cd frontend
npm run build
```

## 本地联调要求

- 后端必须运行在 `localhost:8000`
- 登录依赖 cookie，会走 `withCredentials: true`
- 本地开发环境下，后端 cookie 不应强制 `Secure`

## 下一步可做工作

优先级建议如下：

1. 收口阅读流页面
   - 继续统一 `PaperDetail` 与 `Digest` 的阅读密度、操作按钮和信息层级
   - 把“扫读 -> 展开摘要 -> 进入详情”做成更顺手的一条路径

2. 增强论文库筛选
   - 增加按日期、tag、分数区间过滤
   - 增加当前筛选条件的可视化和一键清空

3. 完善设置页
   - 把来源、LLM、调度拆成更清晰的分区或子页
   - 增加配置变更摘要，避免用户保存前不知道改了什么

4. 优化关键词管理
   - 支持表格内直接编辑权重
   - 增加来源过滤、批量导入和冲突提示

5. 增加真实前端验收
   - 补 Playwright 冒烟测试
   - 覆盖登录、digest 浏览、关键词增删改、设置保存
