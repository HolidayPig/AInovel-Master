# Windows 本机调试运行指南

本文说明在 Windows 上从零启动 AI 小说助手并进行调试的完整步骤。

---

## 一、环境准备

### 1. 安装 Python（后端）

- 推荐 **Python 3.10 或 3.11**（3.12 也可）。
- 下载：https://www.python.org/downloads/
- 安装时勾选 **“Add Python to PATH”**。
- 验证：打开 **PowerShell** 或 **命令提示符**，执行：
  ```powershell
  python --version
  ```
  应显示类似 `Python 3.10.x` 或 `3.11.x`。

### 2. 安装 Node.js（前端）

- 推荐 **Node.js 18 或 20**（LTS）。
- 下载：https://nodejs.org/
- 安装后验证：
  ```powershell
  node --version
  npm --version
  ```
  应分别显示版本号。

### 3. 获取项目代码

- 将项目放在本地目录，例如：`D:\AI\AInovel-Master`。
- 在终端中进入项目根目录：
  ```powershell
  cd D:\AI\AInovel-Master
  ```

---

## 二、启动步骤

需要同时运行 **后端** 和 **前端**，建议开两个终端窗口。

### 步骤 1：启动后端

1. 打开第一个 **PowerShell** 或 **命令提示符**。
2. 进入项目根目录后，再进入后端目录并安装依赖、启动服务：
   ```powershell
   cd D:\AI\AInovel-Master\backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   或一行（在项目根目录执行）：
   ```powershell
   cd D:\AI\AInovel-Master\backend; pip install -r requirements.txt; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
3. 看到类似输出即表示后端已启动：
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000
   INFO:     Application startup complete.
   ```
4. **保持此窗口不要关闭**。

### 步骤 2：启动前端

1. 再打开一个 **PowerShell** 或 **命令提示符**。
2. 进入前端目录并安装依赖、启动开发服务器：
   ```powershell
   cd D:\AI\AInovel-Master\frontend
   npm install
   npm run dev
   ```
3. 看到类似输出即表示前端已启动：
   ```
   VITE v5.x.x  ready in xxx ms
   ➜  Local:   http://localhost:5173/
   ```
4. **保持此窗口不要关闭**。

### 步骤 3：在浏览器中打开应用

1. 打开浏览器（Chrome / Edge 等）。
2. 访问：**http://localhost:5173**
3. 应看到「AI 小说助手」界面：左侧小说/章节列表，中间编辑区，右侧属性卡片。

---

## 三、基本调试操作

| 操作 | 说明 |
|------|------|
| **新建小说** | 左侧「小说列表」旁点击 **+**。 |
| **新建章节** | 先选中一本小说，再在「章节列表」旁点击 **+**。 |
| **编辑正文** | 选中章节后，在中间区域用富文本编辑器编写或修改。 |
| **AI 续写** | 在底部输入框填写续写提示，点击「发送」或按 **Ctrl+Enter**。首次使用前需在右上角「设置」中配置 API Key 和模型；xAI/Grok 配置下可在输入框下方选择本次「联网/不联网」。 |
| **角色/世界观卡片** | 右侧栏可新建、编辑、删除卡片；支持「一键更新」、单卡片「更新」、以及「联网查询」（会先展示新旧对比，确认后覆盖）。 |
| **章节排序** | 在章节列表中拖拽章节项即可调整顺序。 |
| **全书生成** | 左侧章节列表标题栏点击「Book」可按章节顺序一键生成全部章节正文；若已有正文会提示选择覆盖或跳过。 |
| **编辑/删除** | 在章节上 **右键**，选择「编辑」可修改章节名/梗概/目标字数；也可删除章节。 |

### 设置 API（必做一步再使用续写）

1. 点击右上角 **「设置」**。
2. 选择或新建一条配置，填写：
   - **服务商**：OpenAI / xAI(Grok) / Anthropic / 自定义。
   - **API Key**：你的密钥（留空则保留已保存的 Key 不变）。
   - **模型**：如 `gpt-4o`、`grok-2`、`claude-3-5-sonnet` 等。
   - **代理地址**（可选）：若使用 Clash 等，填如 `http://127.0.0.1:7890`。
3. 点击 **「保存」**。

> 提示：联网开关已移动到底部输入框下方工具栏，由用户每次发送时决定是否允许联网。

---

## 四、常见问题排查

### 1. 后端启动报错：`pip` 或 `uvicorn` 找不到

- **pip**：先执行 `python -m pip install -r requirements.txt`。
- **uvicorn**：用 `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` 从项目根目录执行时，需确保当前目录为 `backend`，或先 `cd backend` 再执行上述命令。

### 2. 前端启动报错：`npm` 找不到

- 确认已安装 Node.js，并重新打开终端后再执行 `npm install` 和 `npm run dev`。
- 如仍报错，可尝试使用 **以管理员身份运行** 的终端，或检查系统环境变量中是否包含 Node 安装路径。

### 3. 浏览器打开 5173 后，续写/列表无数据或报错

- 确认 **后端已启动** 且终端无报错（地址为 http://127.0.0.1:8000）。
- 在浏览器中直接访问 http://127.0.0.1:8000/api/health ，应返回 `{"status":"ok"}`。
- 若使用代理/VPN，确保前端开发服务器（Vite）的代理配置指向正确的后端地址（本项目已配置 `/api` → `http://127.0.0.1:8000`）。

### 4. 数据库文件在哪里？

- 默认在项目根目录下的 **`data`** 文件夹中，文件名为 `ainovel.db`。
- 若不存在，首次运行后端并访问一次接口后会自动创建。

### 5. 修改代码后如何看到效果？

- **后端**：使用 `--reload` 时，保存 Python 文件后 Uvicorn 会自动重启，无需手动操作。
- **前端**：Vite 支持热更新，保存 Vue/TS 文件后，浏览器通常会自动刷新或局部更新。

---

## 五、快速命令汇总（复制即用）

在 **项目根目录** `D:\AI\AInovel-Master` 下：

**终端 1（后端）：**
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**终端 2（前端）：**
```powershell
cd frontend
npm install
npm run dev
```

然后浏览器访问：**http://localhost:5173**。
