# SmartCare 智能客服 Agent

一个可运行、可演示、可解释的电商智能客服项目，对应简历中的“智能客服 Agent 系统”。项目实现了 FAQ RAG、订单/物流/退款工具调用、Redis 多轮记忆、退款二次确认、用户数据隔离、反馈采集和 Docker 部署。

> 本仓库提供 **离线 Demo 模式**：不需要模型 API 或下载 BGE-M3 即可跑通核心业务和测试。生产配置可以切换到 **BGE-M3 + FAISS**，并通过 OpenAI-compatible 接口接入 Qwen 服务。

## 架构

```text
Vue3 Web
   │
FastAPI /api/v1/chat
   │
Intent Router ───── FAQ ── Query → Retriever → Evidence Answer
   │                         ├─ Demo: lexical retrieval
   │                         └─ Prod: BGE-M3 + FAISS
   ├──── Order Tool ─────── ownership check → SQLite/MySQL
   ├──── Logistics Tool ─── ownership check → logistics adapter
   └──── Refund Tool ────── validation → 5-minute confirmation → idempotent write
   │
Redis Session Memory（不可用时自动退化为进程内记忆）
```

## 简历需求对应

| 简历描述 | 项目实现 |
|---|---|
| 自建 RAG + Agent | `CustomerServiceAgent` 的 FAQ 与工具双路由 |
| BGE-M3 + FAISS | `BgeM3FaissRetriever`，安装 `requirements-ai.txt` 后启用 |
| Query 改写/多轮记忆 | Qwen 结构化改写 + 离线指代改写；会话上下文与 Redis 隔离 |
| 订单/物流/退款工具 | JSON 结构化工具结果与 trace |
| 退款二次确认 | 5 分钟 token、用户归属校验、服务端规则和幂等键 |
| Vue3 + FastAPI | Vite Vue3 客服台和 FastAPI OpenAPI |
| Redis + Docker + Nginx | Compose 三服务部署，Redis AOF 与 Nginx 反代 |
| FAQ 测试集 | 后端自动化测试覆盖 RAG、越权、二次确认和幂等 |

## 快速开始

### 方式一：Docker（推荐面试演示）

```bash
cp .env.example .env
docker compose up --build
```

打开 <http://localhost:8080>，API 文档位于 <http://localhost:8080/docs>（也可直接访问后端 8000 端口，若自行映射）。

### 方式二：本地开发

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

另开终端：

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>，FastAPI 文档为 <http://localhost:8000/docs>。

## 演示问题

- `会员积分多久过期？`
- `查询订单 ORD-20260801`
- `ORD-20260801 物流到哪了？`
- `订单 ORD-20260802 申请退款，不想要了`
- 越权测试：`查询订单 ORD-OTHER001`

## 启用 BGE-M3 + FAISS

```bash
pip install -r backend/requirements-ai.txt
```

将 `.env` 修改为：

```env
EMBEDDING_PROVIDER=bge-m3
EMBEDDING_MODEL=BAAI/bge-m3
```

第一次启动会下载模型。面试时如果网络或显存不稳定，建议使用默认 lexical 模式演示业务闭环，再说明生产环境的 BGE-M3/FAISS 切换方式。

## 接入 Qwen2/兼容模型

项目使用 OpenAI-compatible `/chat/completions` 接口和 JSON Schema，完成意图分类、订单号/退款原因抽取和多轮 Query Rewrite。修改 `.env`：

```env
DEMO_MODE=false
LLM_BASE_URL=http://你的-qwen-服务/v1
LLM_API_KEY=your-key
LLM_MODEL=qwen2.5-7b-instruct
```

模型只负责生成结构化“调用建议”；订单归属、退款规则、二次确认和数据库写入仍由服务端确定性代码控制。

## API 示例

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"ORD-20260801 物流到哪了？","session_id":"demo-1","user_id":"demo-user"}'
```

## 安全设计

- 订单查询始终使用 `order_id + user_id`，防止水平越权。
- 模型/路由只提出工具请求，数据库操作由服务端确定性规则执行。
- 退款必须二次确认，token 五分钟过期，并使用幂等键避免重复退款。
- 敏感操作拒绝跨用户确认；生产环境应再接入真实登录鉴权和审计平台。
- 知识不足时明确拒答，避免无证据生成。

## 测试

```bash
cd backend
pytest -q
```

测试覆盖：FAQ 检索、订单越权、退款确认、跨用户拒绝和重复退款幂等。

## 面试讲解建议

1. 先讲为什么不是纯聊天机器人：FAQ 用 RAG，真实业务用受控 Tool Calling。
2. 强调退款不是由模型直接执行，而是服务端校验、二次确认、幂等写入。
3. 展示工具 trace 与引用来源，说明系统可观测、可评测。
4. 说明 Demo 模式与生产模式的差异，不把离线样例包装成真实线上 2000+ 咨询。

## 后续生产化路线

- 接入真实 Qwen2.5/OpenAI-compatible 推理服务完成意图分类、参数抽取和 Query Rewrite。
- 使用 MySQL/PostgreSQL 替换 SQLite，增加 Alembic 迁移与连接池监控。
- 接入 Reranker、离线评测集、Prompt 版本管理和 OpenTelemetry trace。
- 增加 OAuth/JWT、限流、熔断、脱敏日志和人工客服转接。
