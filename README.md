# AI 小说助手（AInovel-Master）

一款 **本地优先** 的 AI 小说写作助手：三栏式编辑体验、小说/章节管理、右侧属性卡片（角色/世界观/设定等），支持流式续写与卡片提炼更新。

**当前版本：v0.3** · 更新日志见 [CHANGELOG.md](CHANGELOG.md)

---

## 功能一览

- **三栏式写作界面**
  - **左侧**：小说家 / 小说列表 / 章节列表（支持拖拽排序）
  - **中间**：章节富文本编辑 + AI 流式续写（可“接受/重新生成”）
  - **右侧**：属性卡片（角色/世界观/设定/剧情线/自定义）
- **小说与章节管理**
  - 小说/章节完整 CRUD
  - 章节右键 **编辑**（章节名/梗概/目标字数）
- **属性卡片（文本化）**
  - 卡片内容以“详细描述文本”为核心，写作时注入系统提示以保持设定一致
  - **一键更新**：按最新小说内容重新提炼全部卡片并直接写回
  - **单卡更新**：对单张卡片提炼，展示新旧对比，确认后覆盖
  - **联网查询**：基于卡片名/描述进行搜索提炼，同样走“新旧对比确认”（并隐藏清洗链接）
- **联网搜索（可选）**
  - xAI/Grok 原生支持
  - 其他模型（如 GLM5 等）如其 API 支持 tools/web_search，可在「设置」中标记**支持联网工具**后启用
- **章节大纲自动生成**
  - 左侧章节列表支持 **Outline**：录入全书梗概/主线/分阶段走向/章数与字数目标，AI 生成全书大纲并拆分为分章标题与每章梗概，自动创建章节
- **全书一键生成（按章节顺序）**
  - 左侧章节列表支持 **Book**：按章节顺序逐章生成正文，并写入章节内容；遇到已有正文可选择“覆盖生成”或“跳过已有”
- **全局 AI 进度条**
  - 顶部展示 AI 任务状态（读取上下文/联网检索/思考/生成中…），并显示“已等待Xs”，便于部署初期排查

---

## 快速开始（Windows 本地开发）

更详细步骤与常见问题见：**[Windows 本机调试指南](docs/Windows本地调试指南.md)**。

### 后端（FastAPI）

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端（Vite）

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问 `http://localhost:5173`。前端会将 `/api` 代理到后端 `http://127.0.0.1:8000`。

---

## 使用说明

### 配置模型（必做）

右上角打开 **设置**：

- **服务商**：OpenAI / xAI(Grok) / Anthropic / 自定义（OpenAI 兼容）
- **API Key**：留空表示不修改已保存 Key
- **模型**：例如 `gpt-4o`、`grok-*`、`claude-*`
- **代理地址（可选）**：例如 `http://127.0.0.1:7890`（必须带协议）
- **自定义 Base URL**：仅自定义服务商需要
- **联网工具（支持/不支持）**：用于声明该模型/接口是否支持联网 tools（实际是否联网由每次发送时开关决定）

### AI 续写（中间栏）

- 在底部输入提示词点击 **发送** 或 **Ctrl+Enter**
- 生成完成后可选择 **接受**（并入正文）或 **重新生成**
- 若当前配置支持联网工具，可在输入框下方工具栏选择本次是否 **联网**

### 卡片更新（右侧栏）

- **一键更新**：重新提炼全部卡片（直接写回）
- **更新**（单卡）：提炼本卡片，弹窗展示新旧对比，确认后覆盖
- **联网查询**：搜索并提炼本卡片，弹窗展示新旧对比；输出中的网址会被隐藏清洗

---

## Docker 部署（Linux）

```bash
docker compose up -d
```

访问 `http://localhost:8080`。数据持久化在 `./data` 目录。

如需代理，可通过环境变量 `HTTP_PROXY` / `HTTPS_PROXY` 配置（例如 Clash）。

---

## 项目结构

- `frontend/`：Vue 3 + Vite + TypeScript + Element Plus
  - `src/components/LeftPanel/`：小说家/小说/章节列表与弹窗
  - `src/components/CenterPanel/`：编辑器、续写交互与输入工具栏
  - `src/components/RightPanel/`：卡片列表、编辑与更新确认
- `backend/`：FastAPI + SQLAlchemy(Async) + SQLite
  - `app/routers/`：REST API（novels/chapters/cards/ai/settings/authors）
  - `app/services/`：AI 接入、卡片提炼、提示注入
- `data/`：SQLite 数据库文件（运行后自动创建 `ainovel.db`）
- `docs/`：使用文档与调试指南

---

## API 接口速览（后端）

后端默认监听 `http://127.0.0.1:8000`，API 前缀为 `/api`。前端开发环境会将 `/api` 代理到后端。

### 健康检查

- `GET /api/health`

### 小说（novels）

- `GET /api/novels`
- `POST /api/novels`
- `GET /api/novels/{novel_id}`
- `PATCH /api/novels/{novel_id}`
- `DELETE /api/novels/{novel_id}`

### 章节（chapters）

- `GET /api/chapters?novel_id=...`
- `POST /api/chapters`
- `GET /api/chapters/{chapter_id}`
- `PATCH /api/chapters/{chapter_id}`（可更新 `title/content/summary/target_words/sort_order`）
- `DELETE /api/chapters/{chapter_id}`
- `POST /api/chapters/generate-from-brief`（根据全书梗概/要求自动生成分章并批量创建）

### 卡片（cards）

- `GET /api/cards?novel_id=...`
- `POST /api/cards`
- `GET /api/cards/{card_id}`
- `PATCH /api/cards/{card_id}`
- `DELETE /api/cards/{card_id}`
- `POST /api/cards/refresh-all`（一键更新全部卡片）
- `POST /api/cards/refresh-one-suggestion`（单卡更新建议：返回新旧内容用于确认）
- `POST /api/cards/search-online`（卡片联网查询：返回建议内容用于确认）
- `POST /api/cards/suggest-from-chapter`（从当前章节正文识别可引入为卡片的候选项）

### AI（ai）

- `POST /api/ai/generate`（SSE 流式，除 `delta` 外还会推送 `status` 用于前端显示“正在读取/思考/联网”等进度）
- `POST /api/ai/suggest-chapter-title`

### 设置（settings）

- `GET /api/settings`
- `POST /api/settings`
- `GET /api/settings/{settings_id}`
- `PATCH /api/settings/{settings_id}`
- `DELETE /api/settings/{settings_id}`

### 小说家（authors）

- `GET /api/authors`
- `POST /api/authors`
- `GET /api/authors/{author_id}`
- `PATCH /api/authors/{author_id}`
- `DELETE /api/authors/{author_id}`

---

## 开发与贡献

### 代码结构约定

- **前端**：`frontend/src/components` 按 UI 区域拆分（Left/Center/Right）
- **后端**：`backend/app/routers` 放路由，`backend/app/services` 放 AI 与业务逻辑

### 常用命令

前端构建：

```bash
cd frontend
npm run build
```

后端语法检查：

```bash
cd backend
python -m compileall app
```

---

## 常见问题

- **PowerShell 运行 npm 报脚本禁止**：临时执行 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` 或用 `npm.cmd`
- **代理地址报 Unknown scheme**：必须写成 `http://127.0.0.1:7890` / `socks5://127.0.0.1:7891`
- **xAI 联网工具报错**：项目已按 xAI 文档使用 `/v1/responses` + `web_search`；如仍失败，多为模型不支持 tools 或网络/代理不可用
- **自定义/兼容模型联网不可用**：请先在「设置」中将“联网工具”标记为支持；若仍报 422/工具 schema 错误，说明该服务端不兼容本项目 tools 协议，需要按其文档调整或关闭联网

---

## License

以仓库实际 License 文件为准（如未提供，可按项目需要补充）。
