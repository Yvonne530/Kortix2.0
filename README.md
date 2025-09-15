🔹 1️⃣ Kortix 2.0 技术说明文档（Markdown）
# Kortix 2.0 技术说明文档

## 版本目标
Kortix 2.0 在保持原有功能的基础上，提升以下方面：
1. **安全性**：强化容器隔离、权限控制、防止 agent 逃逸。
2. **可扩展性与性能**：预热容器池、异步任务队列、弹性伸缩。
3. **成本优化**：模型路由、缓存重复请求、按需调用高成本云模型。
4. **可观测性**：Tracing、Prometheus/Grafana 指标监控、报警。
5. **开发者体验**：本地开发模式、热重载、mock LLM、CI 集成。
6. **UX / Agent Builder**：模板、版本管理、policy 管理。

## 1. 架构改进
- **Backend API**：
  - 增加 OpenTelemetry tracing、Prometheus metrics。
  - 健康检查 endpoint `/healthz` 与 `/readyz`。
  - 模型路由中间件，根据请求类型选择本地 / 云 LLM。
  - 异步队列处理长任务（QStash / Redis / RabbitMQ）。
- **Agent Runtime**：
  - 预热容器池，减少冷启动延迟。
  - 安全加固：非 root 用户、read-only filesystem、seccomp/AppArmor。
  - Docker 多阶段构建，减少 attack surface。
- **Frontend Dashboard**：
  - 增加 agent 模板库、版本管理、policy 管理。
  - 支持回放功能以复现会话。
- **Database / Storage**：
  - 对关键表建立索引和分区，Large files 放对象存储，DB 仅存元数据。
  - 数据保留策略与冷存储。

## 2. 安全策略
- Agent 容器：
  - `USER nonroot`、`no-new-privileges`
  - `--cap-drop=ALL`，`read-only` 根文件系统
  - 限制网络访问，仅允许后端与 LLM endpoint
  - Secrets 使用 Vault / cloud secret manager
- 高风险操作需审批或双签。

## 3. 可扩展性与性能
- 异步任务队列 + worker pool
- k8s HPA / serverless container pool
- 冷启动优化：warm pool 预热浏览器与 runtime

## 4. 成本优化
- Model Router：
  - 请求类型、tenant、复杂度决定调用模型
  - 本地 LLM / embeddings 优先
  - 高成本云 LLM 按需调用
- 结果缓存 / 微批请求合并
- Prometheus 统计成本，dashboard 可查看每请求花费

## 5. 可观测性
- OpenTelemetry traces + Jaeger
- Prometheus metrics：
  - agent active count
  - queue length
  - LLM latency
  - failed tasks
  - container start time
- Grafana dashboard + 警报

## 6. 开发者体验
- docker-compose.dev.yaml
- mock LLM
- 热重载
- replay 功能

## 7. 部署与 CI
- docker-compose.prod.yaml + HPA
- GitHub Actions matrix：lint / unit test / integration
- 可回放的 session 测试

## 8. UX / Agent Builder
- 模板库
- 版本管理 + diff view
- Policy / safety templates

🔹 2️⃣ 安全加固 Dockerfile + Run Flags
# Dockerfile.agent (multi-stage)
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip && pip install poetry && poetry export -f requirements.txt --output requirements.txt
RUN pip install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app /app
COPY agent_runtime /app/agent_runtime
USER 1000:1000
RUN mkdir -p /tmp/runtime && chmod 777 /tmp/runtime
CMD ["python", "agent_runtime/main.py"]


Docker run flags：

docker run --rm \
  --user 1000:1000 \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --security-opt seccomp=/path/to/seccomp.json \
  --read-only \
  -v /tmp/runtime:/tmp:rw \
  kortix-agent:2.0

🔹 3️⃣ FastAPI Observability + Health Endpoints
# backend/middleware/observability.py
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
import time
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_latency_seconds', 'Request latency', ['endpoint'])

def setup(app: FastAPI):
    FastAPIInstrumentor.instrument_app(app)
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        REQUEST_COUNT.labels(request.method, request.url.path).inc()
        REQUEST_LATENCY.labels(request.url.path).observe(time.time() - start)
        return response

    @app.get("/metrics")
    async def metrics():
        return Response(generate_latest(), media_type="text/plain")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        # 可加入 DB / Redis / LLM 健康检查
        return {"status": "ready"}

🔹 4️⃣ Model Router Python 示例 + YAML 策略
# backend/model_router.py
import os

MODEL_POLICY = {
    "simple": "local_llm",
    "research": "openai",
    "high_cost": "anthropic"
}

def route_model(request_type: str):
    # 可拓展：按 tenant / cost threshold / token count
    return MODEL_POLICY.get(request_type, "local_llm")

# backend/model_policy.yaml
default: local_llm
policies:
  - type: simple
    model: local_llm
  - type: research
    model: openai
  - type: high_cost
    model: anthropic

🔹 5️⃣ docker-compose.dev.yaml（本地开发）
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENV=dev
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - mock_llm

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  mock_llm:
    image: python:3.11-slim
    command: python -m http.server 9000
    ports:
      - "9000:9000"


启动命令：

make dev   # 或 docker-compose -f docker-compose.dev.yaml up --build

🔹 6️⃣ Grafana Dashboard JSON & Prometheus Metrics 清单

关键 metrics：

http_requests_total{method,endpoint}
http_request_latency_seconds{endpoint}
agent_active_count
queue_length
llm_latency_seconds
container_start_time_seconds
failed_tasks_total


Grafana：

面板：

Agent 活跃数（Gauge）

队列长度（Line / Alert if > threshold）

LLM 延迟（Histogram / Percentiles）

Container 冷启动时间

Task failure rate + alert

警报：

queue length > 50 -> Slack/PagerDuty

failed tasks > 10% -> Slack

LLM latency 95th percentile > 3s -> Slack

可以直接导入 JSON，我这里就不贴完整 JSON（可根据 metrics 清单生成）。
