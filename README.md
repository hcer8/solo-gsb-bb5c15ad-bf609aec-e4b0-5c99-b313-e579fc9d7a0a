# 缺分隔电报码校读 API

基于 Python + FastAPI 的无分隔摩尔斯点划记录校读服务。服务内置 26 个大写英文字母的国际摩尔斯字母表，在 1～6 个候选词的所有可能拼接中进行全局动态规划，选择与输入记录编辑距离最小的词序列。

候选词可以重复使用；点划的**插入、删除、替换**各计 1 次编辑。若最少编辑次数相同，优先选择词数更少的序列；仍相同时选择词序列字典序最小者。

## 一条命令启动

```bash
docker compose up --build -d
```

停止服务：

```bash
docker compose down
```

> 如你的环境使用 Compose V1，请改用 `docker-compose up --build -d`。

## 配置

在启动命令前通过环境变量覆盖配置，或创建 `.env` 文件：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST_PORT` | `8000` | 宿主机映射端口 |
| `APP_PORT` | `8000` | 容器内 Uvicorn 监听端口 |

例如宿主机使用 `18000`，容器内仍使用 `8000`：

```bash
HOST_PORT=18000 docker compose up --build -d
```

## 接口地址

服务启动后可访问：

| 地址 | 说明 |
| --- | --- |
| `http://localhost:8000/health` | 健康检查 |
| `http://localhost:8000/` | 服务信息 |
| `http://localhost:8000/api/decode` | 校读接口（POST） |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/openapi.json` | OpenAPI 描述 |

如果设置了 `HOST_PORT=18000`，请把 URL 中的端口替换为 `18000`。

## 调用样例

```bash
curl -X POST http://localhost:8000/api/decode \
  -H 'Content-Type: application/json' \
  -d '{
    "record": "...---...",
    "candidates": ["SOS", "ET", "A"]
  }'
```

响应：

```json
{
  "words": ["SOS"],
  "morse": "...---...",
  "edits": 0
}
```

再看一个需要全局决定词边界的例子：

```bash
curl -X POST http://localhost:8000/api/decode \
  -H 'Content-Type: application/json' \
  -d '{
    "record": "...",
    "candidates": ["E", "S"]
  }'
```

`S` 对应 `...`，`E E` 也拼成 `...`。编辑次数同为 0，但词数更少，因此返回：

```json
{
  "words": ["S"],
  "morse": "...",
  "edits": 0
}
```

## 请求与响应

### `POST /api/decode`

请求体：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `record` | string | 必填；长度 1～60；只能包含点 `.` 和划 `-` |
| `candidates` | string[] | 必填；1～20 个候选词；每个词长度 1～12，只能包含大写英文字母 `A-Z` |

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `words` | string[] | 最优词序列，长度为 1～6 |
| `morse` | string | `words` 按序无分隔拼接后的标准摩尔斯点划串 |
| `edits` | integer | 输入记录到 `morse` 的最少编辑次数 |

非法 JSON、字段缺失、字段超长、字符不合法或候选数量越界都会返回 HTTP `400 Bad Request`。

## 本地测试

核心算法不依赖 Web 框架，可直接使用系统 Python 运行：

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

镜像构建时会通过 `requirements.txt` 安装 FastAPI、Uvicorn 和 Pydantic。

## 实现说明

程序不会先贪心决定词边界，也不会逐词独立纠错。动态规划以“整个候选词”为扩展单位：

1. 为每个候选词建立标准摩尔斯编码；
2. 在输入记录与候选词编码之间维护完整 Levenshtein 编辑距离网格；
3. 每个词结束时，把该词的所有可能对齐结果并入下一层词边界；
4. 第 1～6 层均参与最终比较；
5. 同一状态按“编辑次数 → 词数 → 词序列字典序”保留唯一最优结果。

这样词边界选择与点划编辑对齐是在同一个全局优化过程中完成的。

## 项目结构

```text
.
├── app/
│   ├── __init__.py
│   ├── decoder.py      # 摩尔斯字母表与全局动态规划
│   └── main.py         # FastAPI 路由、校验和错误处理
├── tests/
│   └── test_decoder.py # 算法测试及小规模穷举对照
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
