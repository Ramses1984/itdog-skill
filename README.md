# 🐕 itdog-client

> itdog.cn 网络测速工具 Python API 客户端

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

纯 Python 实现，无需浏览器，支持从全国/海外节点进行 Ping 测试和 HTTP 网站测速。

## ✨ 功能特性

- 🌍 **Batch Ping** - 从多个节点批量 Ping 测试 IP/域名
- 🌐 **HTTP 测速** - 测试网站在各节点的响应时间
- 🔒 **反爬虫处理** - 自动处理 guard/guardret Cookie
- ⚡ **实时结果** - 通过 WebSocket 实时接收测速数据
- 📊 **多节点支持** - 覆盖三大运营商 + 海外节点

## 📦 安装

```bash
pip install requests websockets
```

## 🚀 快速开始

### Batch Ping

```python
from scripts.itdog_client import batch_ping

def on_result(r):
    print(f"IP: {r['ip']}, 延迟: {r['result']}ms, 节点: {r['node_id']}")

# 从北京三网节点测试 Cloudflare DNS
batch_ping("1.1.1.1", "1310,1273,1250", on_result)
```

输出示例：
```
IP: 1.1.1.1, 延迟: 85ms, 节点: 1310
IP: 1.1.1.1, 延迟: 226ms, 节点: 1250
IP: 1.1.1.1, 延迟: 287ms, 节点: 1273
```

### HTTP 测速

```python
from scripts.itdog_client import http_test

def on_result(r):
    print(f"{r['name']}: {r['all_time']}s (HTTP {r['http_code']})")

http_test("https://www.baidu.com", on_result)
```

## 📍 常用节点

| 节点组 | 节点 ID | 说明 |
|--------|---------|------|
| 北京三网 | `1310,1273,1250` | 电信/联通/移动 |
| 上海三网 | `1227,1254,1249` | 电信/联通/移动 |
| 广深三网 | `1169,1278,1290` | 电信/联通/移动 |
| 海外节点 | `1315,1316,1213` | 香港/新加坡/日本 |

完整节点列表见 [references/nodes.md](references/nodes.md)

## 📖 API 文档

### `batch_ping(host, node_id, callback, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | str / list | - | IP/域名，支持 CIDR |
| node_id | str | - | 节点 ID，逗号分隔 |
| callback | callable | - | 结果回调函数 |
| cidr_filter | bool | True | 过滤网络/广播地址 |
| gateway | str | "last" | 网关位置 |
| timeout | int | 10 | WebSocket 超时(秒) |

**回调数据格式:**
```python
{
    'ip': '1.1.1.1',
    'result': '85',           # 延迟(ms)
    'node_id': '1310',
    'task_num': 1,
    'address': 'cloudflare.com'
}
```

### `http_test(url, callback, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| url | str | - | 测试 URL |
| callback | callable | - | 结果回调函数 |
| check_mode | str | "fast" | 检测模式 |
| method | str | "get" | HTTP 方法 |
| timeout | int | 10 | WebSocket 超时(秒) |

**回调数据格式:**
```python
{
    'name': '北京电信',
    'ip': '220.181.111.1',
    'all_time': '0.050',      # 总耗时(秒)
    'dns_time': '0.005',
    'connect_time': '0.005',
    'download_time': '0.023',
    'http_code': 200,
    'address': '中国/北京/电信'
}
```

## 🎯 使用场景

### Cloudflare CDN 优选

```python
from scripts.itdog_client import ItdogClient

client = ItdogClient()
results = []

def collect(r):
    if r.get('result') and r['result'].isdigit():
        results.append({
            'ip': r['ip'],
            'latency': int(r['result']),
            'location': r.get('address', '')
        })

# 测试多个 Cloudflare IP
client.batch_ping(
    ["104.16.0.1", "104.17.0.1", "172.67.0.1"],
    "1310,1273,1250",
    collect
)

# 按延迟排序，选择最优 IP
for r in sorted(results, key=lambda x: x['latency'])[:3]:
    print(f"{r['ip']}: {r['latency']}ms")
```

### 网站可用性监控

```python
from scripts.itdog_client import http_test

errors = []

def check(r):
    if r.get('http_code') != 200:
        errors.append(f"{r['name']}: HTTP {r.get('http_code')}")

http_test("https://your-website.com", check)

if errors:
    print("⚠️ 异常节点:", errors)
else:
    print("✅ 全部正常")
```

## ⚠️ 注意事项

1. **节点可用性**: 海外节点可能临时不可用，建议优先使用国内节点
2. **请求频率**: 避免高频请求，以免被限制
3. **常量更新**: `TASK_TOKEN_SECRET` 等常量可能需要定期更新

## 🔧 技术细节

详见 [references/api.md](references/api.md)

## 📄 License

MIT License

## 🙏 致谢

- [itdog.cn](https://www.itdog.cn) - 提供测速服务
