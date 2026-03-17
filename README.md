# AI 小说助手 (AInovel-Master)

基于 Vue 3 + FastAPI + SQLite 的 AI 小说写作助手，支持三栏式编辑、角色/世界观卡片与 AI 续写。

**当前版本：v0.2.4** · 更新日志见 [CHANGELOG.md](CHANGELOG.md)

## 本地开发 (Windows)

详细步骤与常见问题见 **[Windows 本机调试指南](docs/Windows本地调试指南.md)**。

### 后端
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```
或从项目根目录：`cd backend && uvicorn app.main:app --reload`

### 前端
```bash
cd frontend
npm install
npm run dev
```
浏览器访问 http://localhost:5173 ，前端会将 `/api` 代理到后端 8000 端口。

## v0.2.4 重要变更

- **联网搜索**：不再在「设置」里常驻开关；改为在底部输入框下方工具栏里，由用户每次发送时选择是否联网（仅 xAI/Grok 配置可见）。
- **卡片更新**：取消「自动更新」；右侧栏新增「一键更新」，以及每张卡片的「更新 / 联网查询」按钮（联网查询会先展示新旧对比，确认后才覆盖；链接会被隐藏清洗）。
- **章节编辑**：章节右键菜单由「重命名」改为「编辑」，可修改章节名/梗概/目标字数。

## Docker 部署 (Linux)

```bash
docker compose up -b
```
访问 http://localhost:8080 。数据持久化在 `./data` 目录。

可通过环境变量 `HTTP_PROXY` / `HTTPS_PROXY` 配置代理（如 Clash）。

## 项目结构

- `frontend/`：Vue 3 + Vite + Element Plus
- `backend/`：FastAPI + SQLAlchemy (SQLite)
- `data/`：SQLite 数据库文件（自动创建）
