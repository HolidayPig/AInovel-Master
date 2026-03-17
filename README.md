# AI 小说助手 (AInovel-Master)

基于 Vue 3 + FastAPI + SQLite 的 AI 小说写作助手，支持三栏式编辑、角色/世界观卡片与 AI 续写。

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
