# Docker 启动说明

项目提供两种 Docker 启动方式。

## 顺序启动

按 Elasticsearch、前端、后端顺序构建镜像并启动容器：

```bash
./scripts/start-sequential.sh
```

可通过环境变量调整宿主机端口：

```bash
ES_HTTP_PORT=9201 FRONTEND_PORT=5174 BACKEND_PORT=8001 ./scripts/start-sequential.sh
```

## Docker Compose 启动

一次性构建并启动前端、后端和 Elasticsearch：

```bash
./scripts/start-compose.sh
```

如果本机 9200、8000 或 5173 已被占用，也可以调整端口：

```bash
ES_HTTP_PORT=9201 BACKEND_PORT=8001 FRONTEND_PORT=5174 ./scripts/start-compose.sh
```

默认访问地址：

- 前端：http://127.0.0.1:5173/
- 后端 API：http://127.0.0.1:8000/api/
- Elasticsearch：http://127.0.0.1:9200/

默认账号：

- 普通用户：demo / demo123456
- 管理员：admin / admin123456
