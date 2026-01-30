#!/usr/bin/env python3
"""
itdog.cn API Client - 网络测速工具
支持 Batch Ping 和 HTTP 测速功能
"""

import re
import json
import base64
import hashlib
import asyncio
import requests
import websockets
from urllib.parse import urlparse
from typing import Callable, Dict, List, Optional, Union

# 固定常量 (可能需要定期更新)
TASK_TOKEN_SECRET = "token_20230313000136kwyktxb0tgspm00yo5"
GUARD_XOR_SUFFIX = "PTNo2n3Ev5"

# 默认 Headers
DEFAULT_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'no-cache',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.itdog.cn',
    'pragma': 'no-cache',
    'sec-ch-ua': '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
}


def _xor_encrypt(input_str: str, key: str) -> str:
    """XOR 加密函数"""
    output = ""
    key = key + GUARD_XOR_SUFFIX
    for i, char in enumerate(input_str):
        char_code = ord(char) ^ ord(key[i % len(key)])
        output += chr(char_code)
    return output


def _generate_guardret(guard: str) -> str:
    """根据 guard Cookie 生成 guardret Cookie (反爬虫机制)"""
    key = guard[:8]
    num = int(guard[12:]) if len(guard) > 12 else 0
    value = num * 2 + 18 - 2  # num * 2 + 16
    encrypted = _xor_encrypt(str(value), key)
    return base64.b64encode(encrypted.encode()).decode()


def _generate_task_token(task_id: str) -> str:
    """根据 task_id 生成 task_token (WebSocket 认证)"""
    full = task_id + TASK_TOKEN_SECRET
    md5_hash = hashlib.md5(full.encode()).hexdigest()
    return md5_hash[8:-8]  # 取中间 16 位


def _extract_from_response(content: str, pattern: str) -> Optional[str]:
    """从 HTML 响应中提取数据"""
    match = re.search(pattern, content)
    return match.group(1) if match else None


class ItdogClient:
    """itdog.cn API 客户端"""

    def __init__(self):
        self.session = requests.Session()

    def _handle_guard_cookie(self, url: str, headers: dict, data: dict):
        """处理反爬虫 Cookie"""
        if 'guardret' not in self.session.cookies:
            self.session.post(url, headers=headers, data=data)

        if 'guard' in self.session.cookies:
            self.session.cookies['guardret'] = _generate_guardret(
                self.session.cookies['guard']
            )

    async def _websocket_receive(
        self,
        wss_url: str,
        task_id: str,
        task_token: str,
        callback: Callable[[Dict], None],
        timeout: int = 10
    ):
        """WebSocket 接收数据"""
        async with websockets.connect(wss_url) as ws:
            await ws.send(json.dumps({
                "task_id": task_id,
                "task_token": task_token
            }))

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    data = json.loads(msg)

                    if data.get('type') == 'finished':
                        break

                    callback(data)

                except asyncio.TimeoutError:
                    # 超时重发请求
                    await ws.send(json.dumps({
                        "task_id": task_id,
                        "task_token": task_token
                    }))
                except json.JSONDecodeError:
                    break

            await ws.close()

    def batch_ping(
        self,
        host: Union[str, List[str]],
        node_id: str,
        callback: Callable[[Dict], None],
        cidr_filter: bool = True,
        gateway: str = "last",
        timeout: int = 10
    ):
        """
        批量 Ping 测速

        Args:
            host: 检测的 IP/域名，可为字符串或列表
            node_id: 节点 ID，逗号分隔，如 "1274,1226"
            callback: 结果回调函数，接收字典参数
            cidr_filter: 是否过滤 CIDR 中的网络/网关/广播地址
            gateway: "last" 或 "first"
            timeout: WebSocket 超时时间(秒)

        Returns:
            回调函数接收的字典格式:
            {
                'ip': '1.0.0.1',
                'result': '171',  # 延迟(ms)
                'node_id': '1274',
                'task_num': 1,
                'address': 'Anycast/cloudflare.com'
            }
        """
        if isinstance(host, str):
            host = [host]

        headers = {
            'Referer': 'https://www.itdog.cn/batch_ping/',
            'User-Agent': DEFAULT_HEADERS['user-agent'],
        }

        data = {
            'host': "\r\n".join(host),
            'node_id': node_id,
            'cidr_filter': 'true' if cidr_filter else 'false',
            'gateway': gateway
        }

        # 处理反爬虫
        self._handle_guard_cookie(
            'https://www.itdog.cn/batch_ping/',
            headers,
            data
        )

        response = self.session.post(
            'https://www.itdog.cn/batch_ping/',
            headers=headers,
            data=data
        )
        content = response.content.decode()

        # 检查错误
        err_match = re.search(r'err_tip_more\("<li>(.*)</li>"\)', content)
        if err_match:
            raise ValueError(err_match.group(1))

        # 提取 WebSocket 参数
        wss_url = _extract_from_response(content, r"var wss_url='(.*)';")
        task_id = _extract_from_response(content, r"var task_id='(.*)';")

        if not wss_url or not task_id:
            raise ValueError("无法从响应中提取 WebSocket 参数")

        task_token = _generate_task_token(task_id)

        asyncio.run(self._websocket_receive(
            wss_url, task_id, task_token, callback, timeout
        ))

    def http_test(
        self,
        url: str,
        callback: Callable[[Dict], None],
        check_mode: str = "fast",
        method: str = "get",
        redirect_num: int = 5,
        dns_server_type: str = "isp",
        custom_headers: Optional[Dict] = None,
        timeout: int = 10
    ):
        """
        HTTP 测速

        Args:
            url: 测试的 URL
            callback: 结果回调函数
            check_mode: "fast" 或 "detail"
            method: HTTP 方法
            redirect_num: 最大重定向次数
            dns_server_type: DNS 服务器类型 ("isp", "custom")
            custom_headers: 自定义请求头 (referer, ua, cookies)
            timeout: WebSocket 超时时间(秒)

        Returns:
            回调函数接收的字典格式:
            {
                'name': '节点名称',
                'ip': 'IP地址',
                'result': '响应时间(ms)',
                'address': '地理位置',
                'head': '响应头状态',
                'task_num': 任务序号
            }
        """
        custom_headers = custom_headers or {}

        headers = {**DEFAULT_HEADERS, 'referer': 'https://www.itdog.cn/http/'}

        data = {
            'line': '',
            'host': url,
            'host_s': urlparse(url).hostname,
            'check_mode': check_mode,
            'ipv4': '',
            'method': method,
            'referer': custom_headers.get('referer', ''),
            'ua': custom_headers.get('ua', ''),
            'cookies': custom_headers.get('cookies', ''),
            'redirect_num': str(redirect_num),
            'dns_server_type': dns_server_type,
            'dns_server': custom_headers.get('dns_server', ''),
        }

        # 处理反爬虫
        self._handle_guard_cookie(
            'https://www.itdog.cn/http/',
            headers,
            data
        )

        response = self.session.post(
            'https://www.itdog.cn/http/',
            headers=headers,
            data=data
        )
        content = response.content.decode()

        # 提取 WebSocket 参数
        wss_url = _extract_from_response(content, r"var wss_url='(.*)';")
        task_id = _extract_from_response(content, r"var task_id='(.*)';")

        if not wss_url or not task_id:
            raise ValueError("无法从响应中提取 WebSocket 参数")

        task_token = _generate_task_token(task_id)

        asyncio.run(self._websocket_receive(
            wss_url, task_id, task_token, callback, timeout
        ))


# 便捷函数
def batch_ping(host, node_id, callback, **kwargs):
    """批量 Ping 测速便捷函数"""
    client = ItdogClient()
    client.batch_ping(host, node_id, callback, **kwargs)


def http_test(url, callback, **kwargs):
    """HTTP 测速便捷函数"""
    client = ItdogClient()
    client.http_test(url, callback, **kwargs)


if __name__ == "__main__":
    # 示例: Batch Ping
    print("=== Batch Ping 测试 ===")
    batch_ping(
        "1.0.0.1",
        "1274,1226",
        lambda r: print(f"IP: {r.get('ip')}, 延迟: {r.get('result')}ms")
    )

    # 示例: HTTP 测速
    print("\n=== HTTP 测速测试 ===")
    http_test(
        "https://www.baidu.com",
        lambda r: print(f"节点: {r.get('name')}, 响应: {r.get('result')}ms")
    )
