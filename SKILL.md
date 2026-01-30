---
name: itdog
description: |
  itdog.cn 网络测速工具 API 客户端。支持 Batch Ping 批量测速和 HTTP 网站测速。
  使用场景: (1) 从全国/海外节点 Ping 测试 IP/域名延迟 (2) HTTP 网站响应测速
  (3) Cloudflare CDN 节点优选 (4) 网络质量诊断
  触发词: itdog, 网络测速, ping测试, 批量ping, http测速, cloudflare优选, 延迟测试
---

# itdog.cn 网络测速工具

纯 Python 实现，无需浏览器。

## 快速开始

```python
from scripts.itdog_client import batch_ping, http_test

# Batch Ping
batch_ping("1.0.0.1", "1274,1226", lambda r: print(r))

# HTTP 测速
http_test("https://www.baidu.com", lambda r: print(r))
```

## 依赖

```bash
pip install requests websockets
```

## API

### batch_ping(host, node_id, callback, ...)

| 参数 | 类型 | 说明 |
|------|------|------|
| host | str/list | IP/域名，支持 CIDR |
| node_id | str | 节点 ID，逗号分隔 |
| callback | callable | 回调函数 |
| cidr_filter | bool | 过滤网络/广播地址 (默认 True) |
| gateway | str | "last"/"first" |
| timeout | int | 超时秒数 (默认 10) |

回调数据:
```python
{'ip': '1.0.0.1', 'result': '171', 'node_id': '1274', 'address': 'cloudflare.com'}
```

### http_test(url, callback, ...)

| 参数 | 类型 | 说明 |
|------|------|------|
| url | str | 测试 URL |
| callback | callable | 回调函数 |
| check_mode | str | "fast"/"detail" |
| method | str | HTTP 方法 |

回调数据:
```python
{
    'name': '北京电信',
    'ip': '220.181.111.1',
    'all_time': '0.050',      # 总耗时(秒)
    'dns_time': '0.005',      # DNS解析时间
    'connect_time': '0.005',  # 连接时间
    'download_time': '0.023', # 下载时间
    'http_code': 200,
    'head': 'HTTP/1.1 200 OK...',
    'address': '中国/北京/电信'
}
```

## 常用节点

- **三网北上广深**: `1310,1273,1250,1227,1254,1249,1169,1278,1290`
- **北京三网**: `1310,1273,1250` (电信/联通/移动)
- **海外**: `1315,1316,1213,1219,1317` ⚠️ 海外节点可能临时不可用
- **Cloudflare 优选**: `1315,1316,1213,1150,1192`

完整节点列表见 [references/nodes.md](references/nodes.md)

> ⚠️ **注意**: 节点可用性会变化，如遇"节点ID不存在"错误，请使用国内节点或检查 itdog.cn 网站获取最新节点列表。

## 技术细节

见 [references/api.md](references/api.md)

## 已知问题

### asyncio 环境兼容性
在某些运行环境中（如已有事件循环的上下文），直接调用 `batch_ping()` 或 `http_test()` 可能导致超时或阻塞。

**推荐方案**: 使用 `timeout` 命令包装或直接运行脚本文件：

```bash
# 方式1: 直接运行内置示例
timeout 30 python3 scripts/itdog_client.py

# 方式2: 命令行调用
timeout 25 python3 -c "
from scripts.itdog_client import batch_ping
batch_ping('1.1.1.1', '1310,1273,1250', lambda r: print(r), timeout=15)
"
```

## 示例: Cloudflare 优选

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

# 测试 Cloudflare IP
client.batch_ping(
    ["104.16.0.1", "104.17.0.1", "172.67.0.1"],
    "1315,1316,1213",  # 香港、新加坡、日本
    collect
)

# 按延迟排序
for r in sorted(results, key=lambda x: x['latency'])[:5]:
    print(f"{r['ip']}: {r['latency']}ms ({r['location']})")
```
