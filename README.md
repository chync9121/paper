# 知识驱动的实验评估与论文生成系统

一个面向 AI 研究与学术写作场景的全栈系统，目标是把“文献梳理 -> 实验管理 -> 自动绘图 -> LaTeX 表格生成 -> 研报撰写 -> 论文装配 -> PDF 编译”串成一条完整工作流。

当前项目已经支持：

- 文献与基准知识图谱构建
- 实验结果看板与对比图绘制
- 顶会风格 LaTeX 表格自动生成
- LLM 驱动的相关工作 / 实验分析生成
- 一键论文工程生成
- 网页实时论文编辑器
- Fake News Detection 主题 Demo 数据与论文 PDF 产出

---

## 1. 项目目标

传统科研写作通常被拆成多个彼此割裂的环节：

- 文献管理在一个工具里
- 实验记录在日志或表格里
- 论文图表靠手工整理
- LaTeX 表格和正文分析靠人工复制粘贴

本项目的核心思路是：

1. 用知识图谱管理论文、模型、数据集、指标之间的关系
2. 用结构化实验数据驱动图表和表格
3. 用统一上下文调用大模型生成学术段落
4. 最终自动装配为论文工程并编译为 PDF

---

## 2. 核心能力

### 2.1 知识图谱

- 录入论文摘要或结构化文献信息
- 存储模型、数据集、指标、任务、方法等节点
- 存储如 `proposed_in`、`evaluated_on`、`introduces_dataset` 等关系
- 前端可视化浏览与交互筛选

### 2.2 实验看板

- 存储实验、run、metric 等结构化数据
- 自动绘制柱状图、折线图、对比图
- 为论文主结果表提供可复用数据底座

### 2.3 顶会级 LaTeX 表格生成

- 遵守 `booktabs` 风格
- 自动最优值加粗、次优值下划线
- 支持多数据集、多指标复杂表头
- 支持消融风格表格生成
- 支持 `resizebox`、`threeparttable`、`table*`

### 2.4 研报与论文生成

- 把图谱上下文与实验结果打包为 prompt context
- 调用 LLM 生成 `Related Work` / `Experimental Analysis`
- 自动生成 `main.tex`、参考文献、图表、PDF

### 2.5 网页实时论文编辑器

- 在线读取 `main.tex`、表格文件、`refs.bib`
- 保存后重新编译 PDF
- 支持自动编译预览
- 右侧 iframe 实时查看 PDF 效果

---

## 3. 技术栈

### 后端

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pandas
- Matplotlib
- NetworkX
- Jinja2
- requests

### 前端

- React 19
- Vite
- Tailwind CSS
- React Router
- ECharts
- React Flow
- Axios

### 论文编译

- MiKTeX

---

## 4. 项目结构

```text
paper/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/                 # FastAPI 路由
│  │  ├─ core/                   # 配置、数据库连接
│  │  ├─ models/                 # SQLAlchemy ORM
│  │  ├─ schemas/                # Pydantic DTO
│  │  ├─ services/               # 图表、表格、LLM、论文生成服务
│  │  └─ templates/              # LaTeX / Jinja2 模板
│  ├─ scripts/                   # Demo 数据脚本、冒烟测试脚本
│  ├─ generated_papers/          # 生成的论文工程与 PDF（默认不提交）
│  ├─ logs/
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ pages/                  # 图谱、实验看板、论文工坊、论文编辑器
│  │  ├─ services/               # 前端 API 封装
│  │  ├─ components/
│  │  └─ types/
│  ├─ public/
│  ├─ package.json
│  └─ .env.example
└─ README.md
```

---

## 5. 已实现的关键页面

前端默认地址：`http://127.0.0.1:3000`

- `/graph`：图谱中心
- `/dashboard`：实验看板 + LaTeX 表格工作台
- `/reports`：LLM 研报生成
- `/paper-studio`：论文自动装配
- `/paper-editor`：网页实时论文编辑器

后端默认地址：`http://127.0.0.1:8000`

- Swagger 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/healthz`

---

## 6. 环境准备

### 6.1 必备软件

- Python 3.11
- Node.js 20+
- PostgreSQL 14+
- Git

### 6.2 可选软件

- MiKTeX
  - 用于把自动生成的 LaTeX 工程编译为 PDF
- 本地代理
  - 默认配置为：
    - `http://127.0.0.1:7890`
    - `https://127.0.0.1:7890`

---

## 7. 配置说明

### 7.1 后端配置

参考文件：`backend/.env.example`

```env
APP_NAME=Knowledge-Driven Evaluation & Report System
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/paper
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=https://127.0.0.1:7890
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TEMPERATURE=0.35
```

### 7.2 前端配置

参考文件：`frontend/.env.example`

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

---

## 8. 本地启动

### 8.1 启动 PostgreSQL

确保已经创建数据库，例如：

```sql
CREATE DATABASE paper;
```

### 8.2 启动后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 8.3 启动前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

---

## 9. Demo 数据

### 9.1 通用实验 Demo

```powershell
cd backend
.venv\Scripts\python.exe scripts\seed_demo_data.py
```

### 9.2 Fake News Detection Demo

用于生成“虚假新闻检测”论文的专题数据：

```powershell
cd backend
.venv\Scripts\python.exe scripts\seed_fake_news_data.py
```

该脚本会写入：

- 论文节点
- 数据集节点：`LIAR`、`FakeNewsNet`、`Fakeddit`
- 模型节点：`BiLSTM`、`DeClarE`、`RoBERTa`、`GraphAware-RoBERTa`
- 指标节点：`Accuracy`、`Macro-F1`、`ROC-AUC`
- 对应实验、runs、metrics

---

## 10. 如何生成论文

### 10.1 通过前端生成

1. 打开 `/paper-studio`
2. 选择图谱节点
3. 选择实验
4. 输入论文标题、目标会场、主要指标
5. 点击“`一键生成论文工程`”

系统会自动生成：

- `main.tex`
- `refs.bib`
- `tables/main_results.tex`
- `tables/ablation.tex`
- `figures/performance_bar.png`
- `figures/metric_scatter.png`
- `main.pdf`（若 MiKTeX 可用）

### 10.2 通过 API 生成

接口：

```http
POST /api/v1/paper-generation/generate
```

示例请求体：

```json
{
  "title": "Knowledge-Driven Fake News Detection",
  "experiment_ids": [4, 5, 6],
  "selected_node_ids": [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26],
  "target_venue": "ACL",
  "main_metric_names": ["Accuracy", "Macro-F1", "ROC-AUC"],
  "prompt": "Write this as a fake news detection benchmark paper.",
  "model_name": "deepseek-chat",
  "use_llm": false,
  "try_compile_pdf": true
}
```

---

## 11. 网页实时论文编辑器

页面地址：

```text
http://127.0.0.1:3000/paper-editor
```

支持：

- 选择已有论文项目
- 加载并编辑：
  - `main.tex`
  - `refs.bib`
  - `tables/main_results.tex`
  - `tables/ablation.tex`
- 保存
- 保存并编译
- 自动编译预览
- 查看编译日志

后端对应接口：

- `GET /api/v1/paper-editor/projects`
- `GET /api/v1/paper-editor/projects/{project_name}/files`
- `GET /api/v1/paper-editor/projects/{project_name}/files/{file_path}`
- `PUT /api/v1/paper-editor/projects/{project_name}/files/{file_path}`
- `POST /api/v1/paper-editor/projects/{project_name}/compile`

---

## 12. 主要后端接口概览

### 论文与图谱

- `POST /api/v1/papers`
- `GET /api/v1/papers`
- `POST /api/v1/graph/nodes`
- `GET /api/v1/graph/nodes`
- `POST /api/v1/graph/edges`
- `GET /api/v1/graph/subgraph`

### 实验管理

- `POST /api/v1/experiments`
- `GET /api/v1/experiments`
- `POST /api/v1/experiments/{experiment_id}/runs`
- `GET /api/v1/experiments/{experiment_id}/runs`
- `POST /api/v1/experiments/runs/{run_id}/metrics/batch`
- `GET /api/v1/experiments/{experiment_id}/metrics`

### 论文表格与报告

- `POST /api/v1/latex/generate`
- `POST /api/v1/reports/generate`
- `GET /api/v1/reports`

### 论文装配与编辑

- `POST /api/v1/paper-generation/generate`
- `GET /api/v1/paper-editor/projects`
- `PUT /api/v1/paper-editor/projects/{project_name}/files/{file_path}`
- `POST /api/v1/paper-editor/projects/{project_name}/compile`

---

## 13. 顶会表格引擎说明

本项目的 LaTeX 表格引擎重点针对 `CVPR / NeurIPS / ACL` 的常见投稿习惯进行了优化：

- 使用 `booktabs`
- 不使用竖线
- 支持 `\toprule` / `\midrule` / `\bottomrule`
- 支持 `\cmidrule`
- 支持最优值加粗
- 支持次优值下划线
- 支持多数据集、多指标嵌套表头
- 支持消融表中的模块勾选展示
- 支持 `resizebox` 防止双栏溢出

---

## 14. 安全说明

### 14.1 API Key 不应提交到仓库

项目根目录已经通过 `.gitignore` 忽略以下敏感内容：

- `backend/.env`
- `frontend/.env`
- `backend/generated_papers/`
- 本地日志
- 虚拟环境
- 前端构建产物

建议做法：

1. 把真实密钥只放在本地 `backend/.env`
2. 对外只提交 `.env.example`
3. 若误泄露，请立刻去供应商控制台轮换密钥

### 14.2 论文产物默认不入库

自动生成的 PDF、LaTeX 中间文件、日志默认不提交，避免：

- 敏感实验内容误公开
- 仓库体积膨胀
- 中间产物污染版本历史

---

## 15. 已验证能力

当前仓库已经完成并验证：

- 后端接口可启动
- 前端页面可访问
- Fake News Detection Demo 数据可写入
- 论文工程可自动生成
- MiKTeX 可用时 PDF 可成功编译
- 网页论文编辑器支持读取、保存、重新编译、刷新 PDF

---

## 16. 后续建议

如果你要把它进一步做成研究型产品，建议继续推进：

1. 接入真实 CSV / JSON 实验上传与自动解析
2. 在论文编辑器中加入“章节模式”编辑
3. 增加引用自动插入与 BibTeX 键生成
4. 加入显著性检验与 `p-value` 标记
5. 增加 GitHub Actions 自动测试与构建
6. 增加 Docker Compose 一键启动

---

## 17. 许可证与使用建议

当前仓库尚未添加正式 License 文件。

如果准备公开发布，建议尽快补充：

- `MIT`
- `Apache-2.0`
- 或与实验数据/模型许可证兼容的其他协议

---

## 18. 致使用者

这个项目更适合被看作一个“研究生产力平台”而不是单一 Demo。

它的价值不只是生成一张图或一段文字，而是把：

- 图谱知识
- 实验数据
- 顶会级表格
- 自动绘图
- 学术写作

这些通常分散的流程，统一成一个可以持续迭代的科研工作台。
