# Kortix 2.0 技术说明文档
This project based on original kortix to make some improvement.

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
