#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口并发测试脚本（支持配置文件）
"""

import asyncio
import aiohttp
import time
import json
import argparse
import csv
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class RequestConfig:
    """请求配置"""
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Dict = field(default_factory=dict)
    timeout: int = 300
    data_source: Optional[Dict] = None
    data_rows: Optional[List[Dict]] = None
    # 流式格式配置
    stream_format: Optional[str] = None  # "sse" 或 None（原始流）
    # SSE 格式配置
    first_token_event: Optional[str] = None  # 用于识别首token的事件类型（如 "workflow_started"）
    completion_event: Optional[str] = None  # 用于识别完成的事件类型（如 "workflow_finished"）
    output_path: Optional[str] = None  # 从事件数据中提取输出的路径（如 "data.outputs.result"）


@dataclass
class RequestMetrics:
    """单个请求的性能指标"""
    request_id: int
    start_time: float
    response_headers_time: Optional[float] = None  # HTTP响应头接收完成时间
    first_token_time: Optional[float] = None      # 第一个数据chunk到达时间
    end_time: Optional[float] = None               # 流式响应结束时间
    total_tokens: int = 0
    total_bytes: int = 0
    error: Optional[str] = None
    events: List[Dict] = field(default_factory=list)  # 记录的事件列表（用于SSE格式）
    
    @property
    def ttft(self) -> Optional[float]:
        """Time To First Token"""
        if self.first_token_time:
            return self.first_token_time - self.start_time
        return None
    
    @property
    def total_time(self) -> Optional[float]:
        """总耗时"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def tokens_per_second(self) -> Optional[float]:
        """token生成速率"""
        if self.total_time and self.total_time > 0:
            return self.total_tokens / self.total_time
        return None


class SSEParser:
    """Server-Sent Events (SSE) 解析器"""
    
    @staticmethod
    def parse_sse_line(line: bytes) -> Optional[Dict[str, Any]]:
        """解析单行 SSE 数据
        
        格式: event: <event_type>\ndata: <json_data>\n\n
        """
        try:
            line_str = line.decode('utf-8', errors='ignore').strip()
            if not line_str:
                return None
            
            result = {}
            
            # 解析 event: 行
            if line_str.startswith('event:'):
                result['event'] = line_str[6:].strip()
            # 解析 data: 行
            elif line_str.startswith('data:'):
                data_str = line_str[5:].strip()
                result['data'] = data_str
                # 尝试解析为 JSON
                try:
                    result['data_json'] = json.loads(data_str)
                except:
                    pass
            # 解析 id: 行
            elif line_str.startswith('id:'):
                result['id'] = line_str[3:].strip()
            # 解析 retry: 行
            elif line_str.startswith('retry:'):
                result['retry'] = line_str[6:].strip()
            
            return result if result else None
        except Exception:
            return None
    
    @staticmethod
    async def parse_sse_stream(stream) -> List[Dict]:
        """解析 SSE 流，返回事件列表
        
        SSE 格式示例:
        event: workflow_started
        data: {"workflow_id": "123"}
        
        event: node_started
        data: {"node_id": "node-1"}
        
        event: workflow_finished
        data: {"node_id": "node-llm-1", "outputs": {"result": "..."}}
        """
        events = []
        buffer = b""
        current_event: Dict[str, Any] = {}
        
        async for chunk in stream:
            if not chunk:
                continue
            
            buffer += chunk
            
            # SSE 格式以 \n\n 分隔完整事件，以 \n 分隔行
            while b'\n\n' in buffer:
                # 提取一个完整的事件块
                event_block, buffer = buffer.split(b'\n\n', 1)
                
                # 解析单个事件块
                event_data: Dict[str, Any] = {}
                for line in event_block.split(b'\n'):
                    if not line.strip():
                        continue
                    parsed = SSEParser.parse_sse_line(line)
                    if parsed:
                        # 合并到当前事件
                        event_data.update(parsed)
                
                # 如果事件有内容，添加到列表
                if event_data:
                    events.append(event_data)
        
        # 处理剩余的 buffer（可能是不完整的事件）
        if buffer.strip():
            for line in buffer.split(b'\n'):
                if not line.strip():
                    continue
                parsed = SSEParser.parse_sse_line(line)
                if parsed:
                    current_event.update(parsed)
            if current_event:
                events.append(current_event)
        
        return events
    
    @staticmethod
    def extract_value(data: Dict, path: str) -> Any:
        """从嵌套字典中提取值
        
        例如: extract_value({"data": {"outputs": {"result": "hello"}}}, "data.outputs.result")
        返回: "hello"
        """
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value


class StreamTester:
    """流式接口并发测试器"""
    
    def __init__(self, config: RequestConfig, concurrency: int = 10, total_requests: int = 100):
        self.config = config
        self.concurrency = concurrency
        self.total_requests = total_requests
        self.metrics: List[RequestMetrics] = []
        self.semaphore = asyncio.Semaphore(concurrency)
        self.completed_count = 0
        self.start_time = None
        
    def _replace_placeholders(self, data: Any, row_data: Dict[str, Any]) -> Any:
        """递归替换数据中的占位符"""
        if isinstance(data, str):
            # 替换占位符 {{column_name}}
            result = data
            for key, value in row_data.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
            return result
        elif isinstance(data, dict):
            return {k: self._replace_placeholders(v, row_data) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_placeholders(item, row_data) for item in data]
        else:
            return data
    
    def _get_request_body(self, request_id: int) -> Dict:
        """获取请求body，如果配置了数据源则替换占位符"""
        if self.config.data_rows:
            # 循环使用数据行
            row_index = (request_id - 1) % len(self.config.data_rows)
            row_data = self.config.data_rows[row_index]
            # 深拷贝body并替换占位符
            body = json.loads(json.dumps(self.config.body))
            return self._replace_placeholders(body, row_data)
        else:
            return self.config.body
    
    async def make_request(self, session: aiohttp.ClientSession, request_id: int) -> RequestMetrics:
        """发送单个流式请求"""
        metric = RequestMetrics(
            request_id=request_id,
            start_time=time.time()
        )
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            # 获取替换后的请求body
            request_body = self._get_request_body(request_id)
            
            async with session.request(
                method=self.config.method,
                url=self.config.url,
                headers=self.config.headers,
                json=request_body,
                timeout=timeout
            ) as response:
                
                if response.status != 200:
                    # 读取错误响应内容以便调试
                    try:
                        error_body = await response.text()
                        # 尝试解析JSON错误信息
                        try:
                            error_json = json.loads(error_body)
                            error_msg = error_json.get('message', error_body)
                        except:
                            error_msg = error_body
                        metric.error = f"HTTP {response.status}: {error_msg[:200]}"
                        print(f"[{request_id:03d}] ❌ 错误详情: {error_msg}")
                    except Exception as e:
                        metric.error = f"HTTP {response.status} (无法读取错误信息: {e})"
                    metric.end_time = time.time()
                    return metric
                
                # 记录HTTP响应头接收完成时间（流式连接建立）
                metric.response_headers_time = time.time()
                
                # 根据配置选择解析方式
                if self.config.stream_format == "sse":
                    # SSE 格式解析 - 实时处理事件
                    events = []
                    buffer = b""
                    current_event: Dict[str, Any] = {}
                    first_token_found = False
                    first_event_time = None
                    event_count = 0
                    
                    async for chunk in response.content.iter_any():
                        if not chunk:
                            continue
                        
                        buffer += chunk
                        metric.total_bytes += len(chunk)
                        
                        # SSE 格式以 \n\n 分隔完整事件
                        while b'\n\n' in buffer:
                            # 提取一个完整的事件块
                            event_block, buffer = buffer.split(b'\n\n', 1)
                            
                            # 解析单个事件块
                            event_data: Dict[str, Any] = {}
                            for line in event_block.split(b'\n'):
                                if not line.strip():
                                    continue
                                parsed = SSEParser.parse_sse_line(line)
                                if parsed:
                                    event_data.update(parsed)
                            
                            # 如果事件有内容，处理它
                            if event_data:
                                events.append(event_data)
                                event_count += 1
                                data_json = event_data.get('data_json', {})
                                
                                # 优先从 data_json 中获取事件类型（Dify 格式）
                                # 如果没有，再从 SSE 的 event: 行获取
                                event_type = ''
                                if isinstance(data_json, dict) and 'event' in data_json:
                                    event_type = data_json.get('event', '')
                                elif 'event' in event_data:
                                    event_type = event_data.get('event', '')
                                
                                # 记录第一个事件的时间（作为备选）
                                if event_count == 1 and not first_token_found:
                                    first_event_time = time.time()
                                
                                # 检查是否是首token事件
                                if not first_token_found:
                                    if self.config.first_token_event:
                                        if event_type == self.config.first_token_event:
                                            metric.first_token_time = time.time()
                                            first_token_found = True
                                            ttft = metric.ttft
                                            print(f"[{request_id:03d}] 流式开始 ({event_type}): {ttft:.3f}s")
                                    elif event_type:  # 如果没有配置，使用第一个有事件类型的事件
                                        metric.first_token_time = time.time()
                                        first_token_found = True
                                        ttft = metric.ttft
                                        print(f"[{request_id:03d}] 流式开始 ({event_type}): {ttft:.3f}s")
                                
                                # 检查是否是完成事件
                                if self.config.completion_event:
                                    if event_type == self.config.completion_event:
                                        # 提取输出数据
                                        if self.config.output_path and data_json:
                                            output = SSEParser.extract_value(data_json, self.config.output_path)
                                            if output:
                                                print(f"[{request_id:03d}] 完成事件 ({event_type}): 输出已提取")
                                elif event_type == 'workflow_finished':  # Dify 默认完成事件
                                    if self.config.output_path and data_json:
                                        output = SSEParser.extract_value(data_json, self.config.output_path)
                                        if output:
                                            print(f"[{request_id:03d}] 完成事件 ({event_type}): 输出已提取")
                    
                    # 处理剩余的 buffer（可能是不完整的事件）
                    if buffer.strip():
                        for line in buffer.split(b'\n'):
                            if not line.strip():
                                continue
                            parsed = SSEParser.parse_sse_line(line)
                            if parsed:
                                current_event.update(parsed)
                        if current_event:
                            events.append(current_event)
                            event_count += 1
                    
                    # 如果没有找到首token事件，使用第一个事件的时间
                    if not first_token_found:
                        if first_event_time:
                            metric.first_token_time = first_event_time
                        elif events:
                            metric.first_token_time = time.time()
                    
                    metric.events = events
                    
                    # 记录结束时间
                    metric.end_time = time.time()
                    metric.total_tokens = len(events)
                    
                    # 打印事件统计
                    event_types = {}
                    for event in events:
                        # 优先从 data_json 中获取事件类型（Dify 格式）
                        data_json = event.get('data_json', {})
                        if isinstance(data_json, dict) and 'event' in data_json:
                            event_type = data_json.get('event', 'unknown')
                        else:
                            event_type = event.get('event', 'unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    event_summary = ', '.join([f'{k}:{v}' for k, v in event_types.items()]) if event_types else '无事件'
                    print(f"[{request_id:03d}] 完成: {metric.total_time:.3f}s | "
                          f"{len(events)} 事件 | {event_summary}")
                else:
                    # 原始流格式（向后兼容）
                    chunk_count = 0
                    stream_started = False
                    buffer = b""
                    
                    async for chunk in response.content.iter_any():
                        if chunk:
                            # 记录首token时间（第一个数据chunk到达）
                            if not stream_started:
                                stream_started = True
                                metric.first_token_time = time.time()
                                ttft = metric.ttft
                                print(f"[{request_id:03d}] 流式开始: {ttft:.3f}s")
                            
                            chunk_count += 1
                            metric.total_bytes += len(chunk)
                            buffer += chunk
                    
                    # 流式结束：async for循环退出表示连接关闭
                    metric.total_tokens = chunk_count
                    metric.end_time = time.time()
                    
                    # 可选：检查是否有明确的结束标记（如SSE格式的 [DONE]）
                    if buffer and b'[DONE]' in buffer:
                        print(f"[{request_id:03d}] 检测到流式结束标记")
                    
                    print(f"[{request_id:03d}] 完成: {metric.total_time:.3f}s | "
                          f"{metric.total_tokens} chunks | "
                          f"{metric.tokens_per_second:.2f} chunks/s | "
                          f"{metric.total_bytes/1024:.2f} KB")
                
        except asyncio.TimeoutError:
            # 整体超时（包括连接超时、读取超时等）
            metric.error = f"Timeout (>{self.config.timeout}s)"
            metric.end_time = time.time()
            elapsed = metric.total_time
            print(f"[{request_id:03d}] ⏱️  超时 (已等待 {elapsed:.2f}s, 超时限制: {self.config.timeout}s)")
        except aiohttp.ServerTimeoutError as e:
            # 服务器响应超时
            metric.error = f"Server Timeout: {str(e)}"
            metric.end_time = time.time()
            elapsed = metric.total_time
            print(f"[{request_id:03d}] ⏱️  服务器超时 (已等待 {elapsed:.2f}s)")
        except aiohttp.ClientConnectorError as e:
            # 连接错误（可能包含连接超时）
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                metric.error = f"Connection Timeout: {str(e)}"
                print(f"[{request_id:03d}] ⏱️  连接超时: {e}")
            else:
                metric.error = f"Connection Error: {str(e)}"
                print(f"[{request_id:03d}] ❌ 连接错误: {e}")
            metric.end_time = time.time()
        except Exception as e:
            # 其他异常
            metric.error = str(e)
            metric.end_time = time.time()
            print(f"[{request_id:03d}] ❌ 错误: {e}")
        
        return metric
    
    async def worker(self, session: aiohttp.ClientSession, request_queue: asyncio.Queue):
        """工作协程 - 保证固定并发数：任务完成后立即领取下一个任务"""
        while True:
            try:
                # 先获取并发许可，确保只有获得许可的worker才能执行任务
                async with self.semaphore:
                    # 获取任务（在semaphore保护下，确保并发控制）
                    request_id = await request_queue.get()
                    
                    if request_id is None:
                        request_queue.task_done()
                        break
                    
                    # 计算当前活跃的并发数
                    active = self.concurrency - self.semaphore._value
                    print(f"\n[{request_id:03d}] 开始 (活跃: {active}/{self.concurrency})")
                    
                    # 执行请求（在semaphore保护下，完成后会自动释放）
                    metric = await self.make_request(session, request_id)
                    self.metrics.append(metric)
                    
                    self.completed_count += 1
                    request_queue.task_done()
                    
                    elapsed = time.time() - self.start_time
                    print(f"进度: {self.completed_count}/{self.total_requests} | "
                          f"已用时: {elapsed:.1f}s")
                    
                    # 任务完成后，semaphore自动释放，worker立即回到循环开始
                    # 再次尝试获取semaphore，如果成功则立即领取下一个任务
                    # 这样保证了始终维持固定并发数
                    
            except Exception as e:
                print(f"Worker错误: {e}")
                # 确保异常时也标记任务完成
                try:
                    request_queue.task_done()
                except ValueError:
                    pass  # 如果任务未在队列中，忽略错误
    
    async def run(self):
        """运行测试"""
        print(f"\n{'='*70}")
        print(f"流式接口并发测试")
        print(f"{'='*70}")
        print(f"URL:        {self.config.url}")
        print(f"并发数:      {self.concurrency}")
        print(f"总请求数:    {self.total_requests}")
        if self.config.data_rows:
            print(f"数据源:      CSV ({len(self.config.data_rows)} 行，将循环使用)")
        if self.config.stream_format:
            print(f"流式格式:    {self.config.stream_format.upper()}")
            if self.config.first_token_event:
                print(f"首Token事件: {self.config.first_token_event}")
            if self.config.completion_event:
                print(f"完成事件:    {self.config.completion_event}")
            if self.config.output_path:
                print(f"输出路径:    {self.config.output_path}")
        print(f"开始时间:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        self.start_time = time.time()
        
        request_queue = asyncio.Queue()
        
        for i in range(self.total_requests):
            await request_queue.put(i + 1)
        
        for _ in range(self.concurrency):
            await request_queue.put(None)
        
        connector = aiohttp.TCPConnector(limit=self.concurrency * 2)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            workers = [
                asyncio.create_task(self.worker(session, request_queue))
                for _ in range(self.concurrency)
            ]
            
            await request_queue.join()
            await asyncio.gather(*workers)
        
        self.print_report()
    
    def print_report(self):
        """打印测试报告"""
        total_elapsed = time.time() - self.start_time
        
        print(f"\n{'='*70}")
        print(f"测试报告")
        print(f"{'='*70}")
        
        successful = [m for m in self.metrics if m.error is None]
        failed = [m for m in self.metrics if m.error is not None]
        
        print(f"\n【总体统计】")
        print(f"  总请求数:    {self.total_requests}")
        print(f"  成功:        {len(successful)} ({len(successful)/self.total_requests*100:.1f}%)")
        print(f"  失败:        {len(failed)} ({len(failed)/self.total_requests*100:.1f}%)")
        print(f"  总耗时:      {total_elapsed:.2f}s")
        print(f"  吞吐量:      {self.total_requests/total_elapsed:.2f} req/s")
        
        if successful:
            ttfts = [m.ttft for m in successful if m.ttft is not None]
            total_times = [m.total_time for m in successful if m.total_time is not None]
            tps_list = [m.tokens_per_second for m in successful if m.tokens_per_second is not None]
            
            if ttfts:
                sorted_ttfts = sorted(ttfts)
                print(f"\n【首Token时间 (TTFT)】")
                print(f"  最小值:      {min(ttfts):.3f}s")
                print(f"  最大值:      {max(ttfts):.3f}s")
                print(f"  平均值:      {statistics.mean(ttfts):.3f}s")
                print(f"  中位数:      {statistics.median(ttfts):.3f}s")
                if len(ttfts) > 1:
                    print(f"  标准差:      {statistics.stdev(ttfts):.3f}s")
                print(f"  P50:         {sorted_ttfts[int(len(sorted_ttfts)*0.50)]:.3f}s")
                print(f"  P90:         {sorted_ttfts[int(len(sorted_ttfts)*0.90)]:.3f}s")
                print(f"  P95:         {sorted_ttfts[int(len(sorted_ttfts)*0.95)]:.3f}s")
                print(f"  P99:         {sorted_ttfts[int(len(sorted_ttfts)*0.99)]:.3f}s")
            
            if total_times:
                sorted_times = sorted(total_times)
                print(f"\n【总耗时】")
                print(f"  最小值:      {min(total_times):.3f}s")
                print(f"  最大值:      {max(total_times):.3f}s")
                print(f"  平均值:      {statistics.mean(total_times):.3f}s")
                print(f"  中位数:      {statistics.median(total_times):.3f}s")
                print(f"  P95:         {sorted_times[int(len(sorted_times)*0.95)]:.3f}s")
                print(f"  P99:         {sorted_times[int(len(sorted_times)*0.99)]:.3f}s")
            
            if tps_list:
                print(f"\n【生成速率】")
                print(f"  平均值:      {statistics.mean(tps_list):.2f} chunks/s")
                print(f"  中位数:      {statistics.median(tps_list):.2f} chunks/s")
                print(f"  最大值:      {max(tps_list):.2f} chunks/s")
        
        if failed:
            print(f"\n【失败详情】")
            error_counts = {}
            for m in failed:
                error_counts[m.error] = error_counts.get(m.error, 0) + 1
            for error, count in error_counts.items():
                print(f"  {error}: {count}次")
        
        print(f"\n{'='*70}\n")
        
        self.save_results()
    
    def save_results(self, filename: str = "data/test_results.json"):
        """保存结果到JSON"""
        results = {
            "config": {
                "url": self.config.url,
                "concurrency": self.concurrency,
                "total_requests": self.total_requests,
                "timestamp": datetime.now().isoformat()
            },
            "summary": {
                "success_count": len([m for m in self.metrics if m.error is None]),
                "failed_count": len([m for m in self.metrics if m.error is not None]),
            },
            "metrics": [
                {
                    "request_id": m.request_id,
                    "ttft": m.ttft,
                    "total_time": m.total_time,
                    "total_tokens": m.total_tokens,
                    "total_bytes": m.total_bytes,
                    "tokens_per_second": m.tokens_per_second,
                    "error": m.error,
                    "events_count": len(m.events) if m.events else None,
                    "events": m.events if m.events else None  # 保存完整的事件数据
                }
                for m in self.metrics
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"详细结果已保存: {filename}")
        
        # 保存调试文件（包含所有原始响应数据）
        self.save_debug_results()
    
    def save_debug_results(self, filename: str = "data/debug_responses.json"):
        """保存调试文件，包含所有请求的完整响应数据"""
        debug_data = {
            "config": {
                "url": self.config.url,
                "method": self.config.method,
                "stream_format": self.config.stream_format,
                "first_token_event": self.config.first_token_event,
                "timestamp": datetime.now().isoformat()
            },
            "total_requests": self.total_requests,
            "requests": []
        }
        
        for m in self.metrics:
            request_data = {
                "request_id": m.request_id,
                "start_time": m.start_time,
                "response_headers_time": m.response_headers_time,
                "first_token_time": m.first_token_time,
                "end_time": m.end_time,
                "ttft": m.ttft,
                "total_time": m.total_time,
                "error": m.error
            }
            
            # 保存完整的事件数据（SSE格式）
            if m.events:
                request_data["events"] = m.events
                request_data["events_count"] = len(m.events)
                
                # 按事件类型分组统计
                event_summary = {}
                for event in m.events:
                    # 优先从 data_json 中获取事件类型（Dify 格式）
                    data_json = event.get('data_json', {})
                    if isinstance(data_json, dict) and 'event' in data_json:
                        event_type = data_json.get('event', 'unknown')
                    else:
                        event_type = event.get('event', 'unknown')
                    if event_type not in event_summary:
                        event_summary[event_type] = []
                    event_summary[event_type].append({
                        "data": event.get('data'),
                        "data_json": event.get('data_json'),
                        "id": event.get('id')
                    })
                request_data["events_by_type"] = event_summary
            
            # 保存原始数据统计
            request_data["total_tokens"] = m.total_tokens
            request_data["total_bytes"] = m.total_bytes
            request_data["tokens_per_second"] = m.tokens_per_second
            
            debug_data["requests"].append(request_data)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        print(f"调试数据已保存: {filename}")


def load_csv_data(csv_file: str, column: Optional[str] = None, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
    """加载CSV文件数据"""
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV文件不存在: {csv_file}")
    
    rows = []
    with open(csv_file, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    if not rows:
        raise ValueError(f"CSV文件为空或格式错误: {csv_file}")
    
    # 如果指定了列名，验证列是否存在
    if column and column not in rows[0]:
        available_columns = ', '.join(rows[0].keys())
        raise ValueError(f"CSV文件中不存在列 '{column}'，可用列: {available_columns}")
    
    return rows


def load_config(config_file: str) -> tuple:
    """从JSON文件加载配置"""
    config_dir = os.path.dirname(os.path.abspath(config_file))
    
    with open(config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 处理数据源配置
    data_source = data.get('data_source')
    data_rows = None
    
    if data_source:
        source_type = data_source.get('type', '').lower()
        if source_type == 'csv':
            csv_file = data_source.get('file')
            if not csv_file:
                raise ValueError("CSV数据源配置中缺少 'file' 字段")
            
            # 处理相对路径
            if not os.path.isabs(csv_file):
                csv_file = os.path.join(config_dir, csv_file)
            
            column = data_source.get('column')
            encoding = data_source.get('encoding', 'utf-8')
            
            data_rows = load_csv_data(csv_file, column, encoding)
            print(f"已加载CSV数据: {csv_file} ({len(data_rows)} 行)")
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")
    
    # 流式格式配置
    stream_config = data.get('stream_format', {})
    
    config = RequestConfig(
        url=data['url'],
        method=data.get('method', 'POST'),
        headers=data.get('headers', {}),
        body=data.get('body', {}),
        timeout=data.get('timeout', 300),
        data_source=data_source,
        data_rows=data_rows,
        stream_format=stream_config.get('type') if isinstance(stream_config, dict) else stream_config,
        first_token_event=stream_config.get('first_token_event') if isinstance(stream_config, dict) else None,
        completion_event=stream_config.get('completion_event') if isinstance(stream_config, dict) else None,
        output_path=stream_config.get('output_path') if isinstance(stream_config, dict) else None
    )
    
    concurrency = data.get('concurrency', 10)
    total_requests = data.get('total_requests', 100)
    
    return config, concurrency, total_requests


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='流式接口并发测试工具')
    parser.add_argument('-c', '--config', type=str, help='配置文件路径 (JSON)')
    parser.add_argument('-u', '--url', type=str, help='接口URL')
    parser.add_argument('-n', '--requests', type=int, default=100, help='总请求数')
    parser.add_argument('-p', '--concurrency', type=int, default=10, help='并发数')
    
    args = parser.parse_args()
    
    if args.config:
        # 从配置文件加载
        config, concurrency, total_requests = load_config(args.config)
    elif args.url:
        # 从命令行参数创建配置
        config = RequestConfig(
            url=args.url,
            headers={"Content-Type": "application/json"},
            body={"stream": True}
        )
        concurrency = args.concurrency
        total_requests = args.requests
    else:
        # 使用默认配置（示例）
        print("未指定配置文件或URL，使用示例配置...")
        config = RequestConfig(
            url="https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer your-api-key"
            },
            body={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            }
        )
        concurrency = 10
        total_requests = 50
    
    tester = StreamTester(
        config=config,
        concurrency=concurrency,
        total_requests=total_requests
    )
    
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())