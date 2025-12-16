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


@dataclass
class RequestMetrics:
    """单个请求的性能指标"""
    request_id: int
    start_time: float
    first_token_time: Optional[float] = None
    end_time: Optional[float] = None
    total_tokens: int = 0
    total_bytes: int = 0
    error: Optional[str] = None
    
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
                    metric.error = f"HTTP {response.status}"
                    metric.end_time = time.time()
                    return metric
                
                # 读取流式响应
                chunk_count = 0
                async for chunk in response.content.iter_any():
                    if chunk:
                        # 记录首token时间
                        if metric.first_token_time is None:
                            metric.first_token_time = time.time()
                            ttft = metric.ttft
                            print(f"[{request_id:03d}] 首token: {ttft:.3f}s")
                        
                        chunk_count += 1
                        metric.total_bytes += len(chunk)
                
                metric.total_tokens = chunk_count
                metric.end_time = time.time()
                
                print(f"[{request_id:03d}] 完成: {metric.total_time:.3f}s | "
                      f"{metric.total_tokens} chunks | "
                      f"{metric.tokens_per_second:.2f} chunks/s | "
                      f"{metric.total_bytes/1024:.2f} KB")
                
        except asyncio.TimeoutError:
            metric.error = "Timeout"
            metric.end_time = time.time()
            print(f"[{request_id:03d}] 超时")
        except Exception as e:
            metric.error = str(e)
            metric.end_time = time.time()
            print(f"[{request_id:03d}] 错误: {e}")
        
        return metric
    
    async def worker(self, session: aiohttp.ClientSession, request_queue: asyncio.Queue):
        """工作协程"""
        while True:
            try:
                request_id = await request_queue.get()
                
                if request_id is None:
                    request_queue.task_done()
                    break
                
                # 控制并发数
                async with self.semaphore:
                    active = self.concurrency - self.semaphore._value
                    print(f"\n[{request_id:03d}] 开始 (活跃: {active}/{self.concurrency})")
                    
                    metric = await self.make_request(session, request_id)
                    self.metrics.append(metric)
                    
                    self.completed_count += 1
                    request_queue.task_done()
                    
                    elapsed = time.time() - self.start_time
                    print(f"进度: {self.completed_count}/{self.total_requests} | "
                          f"已用时: {elapsed:.1f}s")
                    
            except Exception as e:
                print(f"Worker错误: {e}")
                request_queue.task_done()
    
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
    
    def save_results(self, filename: str = "test_results.json"):
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
                    "error": m.error
                }
                for m in self.metrics
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"详细结果已保存: {filename}")


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
    
    config = RequestConfig(
        url=data['url'],
        method=data.get('method', 'POST'),
        headers=data.get('headers', {}),
        body=data.get('body', {}),
        timeout=data.get('timeout', 300),
        data_source=data_source,
        data_rows=data_rows
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