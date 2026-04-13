# Travel Sharing and Community Platform

基于 `Django REST Framework + Vue 3` 的旅游分享与交流平台毕业设计项目。
项目运行在本地，部分中间件使用远程服务器提供。

## 已实现模块

- 用户注册、登录、JWT 鉴权、个人信息读取
- 目的地与酒店信息展示、关键词搜索、小众目的地筛选
- 社区攻略发布、帖子列表、点赞互动
- 管理员审核帖子与评论，未审核内容不会公开展示
- 评论回复与多级展示
- 智能行程生成与个人行程记录
- 基于用户行为的轻量推荐
- MinIO 图片上传
- ElasticSearch 检索与数据库回退搜索
- 集成 Kimi / 千问大模型，支持 AI 行程顾问与 AI 内容润色
- Django Admin 后台管理

## 项目结构

- `backend/`：Django + DRF 后端
- `frontend/`：Vue 3 + Vite 前端
- `开题报告.txt`：需求来源
- `中间件信息.txt`：已有中间件信息

## 中间件使用方式

- 项目代码运行在本地
- 数据库：远程 MySQL
- 缓存：远程 Redis
- 对象存储：远程 MinIO
- 搜索：本地 ElasticSearch

默认配置已写入 `backend/.env`。

## 大模型接入

- 已接入 `Kimi` 与 `千问`
- 前端可在行程规划页选择模型生成 AI 旅行建议
- 前端可在社区发帖弹窗中使用 AI 润色标题、正文和标签
- 后端统一入口在 `api/ai/`

## 本地启动

后端：

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py ensure_admin --username admin --password admin123456 --email admin@example.com
.\.venv\Scripts\python.exe backend\manage.py init_external_services
.\.venv\Scripts\python.exe backend\manage.py runserver
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

## 演示账号

- 用户名：`demo`
- 密码：`demo123456`
- 管理员：`admin`
- 密码：`admin123456`

## 环境配置

- 当前 `backend/.env` 已切到远程 `MySQL / Redis / MinIO` 与本地 `ElasticSearch`
- 如果要改回其他环境，可参考 `backend/.env.example`
- 前端接口地址可参考 `frontend/.env.example`
