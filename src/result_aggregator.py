"""
Result Aggregator - 结果聚合器
负责收集、整合和格式化多Agent的执行结果
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from abc import ABC, abstractmethod
import logging


@dataclass
class AgentResult:
    """单个Agent的结果"""
    agent_id: str
    agent_type: str
    agent_name: str
    task_id: str
    task_title: str
    status: str
    output_file: str
    content: str
    duration_minutes: float
    timestamp: str


@dataclass
class AggregatedReport:
    """聚合报告"""
    title: str
    summary: str
    sections: List[dict]
    metadata: dict
    generated_at: str
    format: str


class ResultFormatter(ABC):
    """结果格式化器基类"""
    
    @abstractmethod
    def format(self, results: List[AgentResult]) -> str:
        """格式化结果"""
        pass
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """格式名称"""
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """文件扩展名"""
        pass


class MarkdownFormatter(ResultFormatter):
    """Markdown格式器"""
    
    @property
    def format_name(self) -> str:
        return "markdown"
    
    @property
    def file_extension(self) -> str:
        return "md"
    
    def format(self, results: List[AgentResult]) -> str:
        lines = []
        
        # 标题
        lines.append("# 多Agent执行结果汇总报告\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**参与Agent**: {len(results)} 个\n")
        
        # 执行摘要
        lines.append("## 📊 执行摘要\n")
        completed = sum(1 for r in results if r.status == "completed")
        failed = sum(1 for r in results if r.status == "failed")
        total_duration = sum(r.duration_minutes for r in results)
        
        lines.append(f"- ✅ 成功: {completed} 个")
        lines.append(f"- ❌ 失败: {failed} 个")
        lines.append(f"- ⏱️ 总耗时: {total_duration:.1f} 分钟")
        lines.append(f"- ⚡ 并行效率: {max(r.duration_minutes for r in results):.1f} 分钟（最长单任务）\n")
        
        # 各Agent结果
        lines.append("## 📝 详细结果\n")
        
        for result in results:
            emoji = {"alpha": "🎯", "beta": "💻", "gamma": "🎨", 
                    "delta": "📊", "omega": "📈"}.get(result.agent_type, "🤖")
            
            lines.append(f"### {emoji} {result.agent_name} ({result.agent_type})\n")
            lines.append(f"**任务**: {result.task_title}")
            lines.append(f"**状态**: {'✅ 完成' if result.status == 'completed' else '❌ 失败'}")
            lines.append(f"**耗时**: {result.duration_minutes:.1f} 分钟")
            lines.append(f"**输出**: `{result.output_file}`\n")
            
            # 内容摘要（前500字符）
            if result.content:
                summary = result.content[:500] + "..." if len(result.content) > 500 else result.content
                lines.append("**内容摘要**:")
                lines.append(f"```\n{summary}\n```\n")
        
        # 关键结论
        lines.append("## 🎯 关键结论\n")
        lines.append("_基于各Agent输出自动提取的关键信息_\n")
        
        for result in results:
            key_points = self._extract_key_points(result.content)
            if key_points:
                emoji = {"alpha": "🎯", "beta": "💻", "gamma": "🎨", 
                        "delta": "📊", "omega": "📈"}.get(result.agent_type, "🤖")
                lines.append(f"### {emoji} {result.agent_name}")
                for point in key_points[:5]:  # 最多5个要点
                    lines.append(f"- {point}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """从内容中提取关键要点"""
        if not content:
            return []
        
        # 查找列表项
        bullet_points = re.findall(r'^[\s]*[-*][\s]+(.+)$', content, re.MULTILINE)
        
        # 查找数字列表
        numbered_points = re.findall(r'^[\s]*\d+[\.\)][\s]+(.+)$', content, re.MULTILINE)
        
        # 查找加粗文字
        bold_points = re.findall(r'\*\*(.+?)\*\*[:：]?\s*(.+?)(?:\n|$)', content)
        
        all_points = bullet_points + numbered_points
        
        # 从加粗文字中提取
        for title, desc in bold_points:
            if len(desc.strip()) > 10:
                all_points.append(f"{title}: {desc.strip()[:100]}")
            else:
                all_points.append(title)
        
        return [p.strip() for p in all_points if len(p.strip()) > 5][:10]


class JSONFormatter(ResultFormatter):
    """JSON格式器"""
    
    @property
    def format_name(self) -> str:
        return "json"
    
    @property
    def file_extension(self) -> str:
        return "json"
    
    def format(self, results: List[AgentResult]) -> str:
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_agents": len(results),
            "summary": {
                "completed": sum(1 for r in results if r.status == "completed"),
                "failed": sum(1 for r in results if r.status == "failed"),
                "total_duration_minutes": sum(r.duration_minutes for r in results)
            },
            "results": [
                {
                    "agent_id": r.agent_id,
                    "agent_type": r.agent_type,
                    "agent_name": r.agent_name,
                    "task_id": r.task_id,
                    "task_title": r.task_title,
                    "status": r.status,
                    "duration_minutes": r.duration_minutes,
                    "timestamp": r.timestamp,
                    "content_preview": r.content[:200] if r.content else ""
                }
                for r in results
            ]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


class HTMLFormatter(ResultFormatter):
    """HTML格式器"""
    
    @property
    def format_name(self) -> str:
        return "html"
    
    @property
    def file_extension(self) -> str:
        return "html"
    
    def format(self, results: List[AgentResult]) -> str:
        completed = sum(1 for r in results if r.status == "completed")
        failed = sum(1 for r in results if r.status == "failed")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>多Agent执行结果汇总</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .summary {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .agent-card {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin: 15px 0; }}
        .agent-header {{ display: flex; align-items: center; margin-bottom: 10px; }}
        .agent-emoji {{ font-size: 24px; margin-right: 10px; }}
        .agent-name {{ font-size: 18px; font-weight: bold; color: #333; }}
        .status-completed {{ color: #4CAF50; }}
        .status-failed {{ color: #f44336; }}
        .meta {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .content {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin-top: 10px; font-family: monospace; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 多Agent执行结果汇总报告</h1>
        
        <div class="summary">
            <p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>参与Agent</strong>: {len(results)} 个</p>
            <p><strong>成功</strong>: {completed} 个 | <strong>失败</strong>: {failed} 个</p>
        </div>
"""
        
        for result in results:
            status_class = "status-completed" if result.status == "completed" else "status-failed"
            status_text = "✅ 完成" if result.status == "completed" else "❌ 失败"
            
            emoji_map = {"🎯":"🎯","💻":"💻","🎨":"🎨","📊":"📊","📈":"📈"}
            agent_emoji = emoji_map.get(result.agent_type, "🤖")
            
            html += f"""
        <div class="agent-card">
            <div class="agent-header">
                <span class="agent-emoji">{agent_emoji}</span>
                <span class="agent-name">{result.agent_name} ({result.agent_type})</span>
            </div>
            <p><strong>任务</strong>: {result.task_title}</p>
            <p class="meta">
                <span class="{status_class}">{status_text}</span> | 
                耗时: {result.duration_minutes:.1f} 分钟
            </p>
            <div class="content">{result.content[:500]}{"..." if len(result.content) > 500 else ""}</div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html


class ResultAggregator:
    """结果聚合器 - 收集和整合多Agent执行结果"""
    
    def __init__(self, shared_dir: str = None):
        """
        初始化结果聚合器
        
        Args:
            shared_dir: 共享目录路径
        """
        self.shared_dir = Path(shared_dir or "~/.openclaw/workspace").expanduser()
        self.shared_tasks_dir = self.shared_dir / "shared_tasks"
        self.shared_results_dir = self.shared_dir / "shared_results"
        
        # 格式化器注册
        self.formatters: Dict[str, ResultFormatter] = {}
        self.register_formatter(MarkdownFormatter())
        self.register_formatter(JSONFormatter())
        self.register_formatter(HTMLFormatter())
        
        # 结果缓存
        self.collected_results: List[AgentResult] = []
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def register_formatter(self, formatter: ResultFormatter):
        """注册格式化器"""
        self.formatters[formatter.format_name] = formatter
    
    def collect_single(self, task_id: str) -> Optional[AgentResult]:
        """
        收集单个任务的结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            AgentResult对象或None
        """
        task_file = self.shared_tasks_dir / f"{task_id}.json"
        
        if not task_file.exists():
            self.logger.warning(f"任务文件不存在: {task_id}")
            return None
        
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            # 读取输出文件内容
            content = ""
            output_file = task_data.get("deliverable", "")
            if output_file and Path(output_file).exists():
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    self.logger.warning(f"读取输出文件失败: {e}")
            
            # 计算耗时
            start = datetime.fromisoformat(task_data.get("started_at", task_data.get("created_at")))
            end = datetime.now()
            if task_data.get("completed_at"):
                end = datetime.fromisoformat(task_data["completed_at"])
            duration = (end - start).total_seconds() / 60
            
            return AgentResult(
                agent_id=task_data.get("agent_id", ""),
                agent_type=task_data.get("agent_type", ""),
                agent_name=task_data.get("agent_name", ""),
                task_id=task_id,
                task_title=task_data.get("title", ""),
                status=task_data.get("status", "unknown"),
                output_file=output_file,
                content=content,
                duration_minutes=duration,
                timestamp=task_data.get("completed_at", datetime.now().isoformat())
            )
            
        except Exception as e:
            self.logger.error(f"收集任务结果失败 {task_id}: {e}")
            return None
    
    def collect_all(self, timeout: int = 300) -> List[AgentResult]:
        """
        收集所有已完成任务的结果
        
        Args:
            timeout: 等待超时时间（秒）
            
        Returns:
            AgentResult列表
        """
        results = []
        
        if not self.shared_tasks_dir.exists():
            return results
        
        for task_file in self.shared_tasks_dir.glob("task_*.json"):
            task_id = task_file.stem
            result = self.collect_single(task_id)
            if result:
                results.append(result)
        
        self.collected_results = results
        self.logger.info(f"收集到 {len(results)} 个任务结果")
        
        return results
    
    def generate_report(self, 
                       results: List[AgentResult] = None,
                       format: str = "markdown",
                       output_file: str = None) -> str:
        """
        生成聚合报告
        
        Args:
            results: 结果列表，None使用已收集的结果
            format: 输出格式 (markdown/json/html)
            output_file: 输出文件路径
            
        Returns:
            格式化后的报告内容
        """
        if results is None:
            results = self.collected_results
        
        if not results:
            return "暂无结果数据"
        
        formatter = self.formatters.get(format)
        if not formatter:
            raise ValueError(f"未知的格式: {format}")
        
        report_content = formatter.format(results)
        
        # 保存到文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.logger.info(f"报告已保存: {output_file}")
        
        return report_content
    
    def get_summary(self, results: List[AgentResult] = None) -> dict:
        """
        获取结果摘要
        
        Args:
            results: 结果列表
            
        Returns:
            摘要字典
        """
        if results is None:
            results = self.collected_results
        
        if not results:
            return {}
        
        completed = [r for r in results if r.status == "completed"]
        failed = [r for r in results if r.status == "failed"]
        
        return {
            "total": len(results),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(results) * 100,
            "total_duration_minutes": sum(r.duration_minutes for r in results),
            "avg_duration_minutes": sum(r.duration_minutes for r in results) / len(results),
            "agent_breakdown": {
                agent_type: len([r for r in results if r.agent_type == agent_type])
                for agent_type in set(r.agent_type for r in results)
            }
        }


# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Result Aggregator CLI")
    parser.add_argument("--collect", "-c", action="store_true", help="收集所有结果")
    parser.add_argument("--report", "-r", help="生成报告 (markdown/json/html)")
    parser.add_argument("--output", "-o", help="输出文件")
    parser.add_argument("--summary", "-s", action="store_true", help="显示摘要")
    
    args = parser.parse_args()
    
    aggregator = ResultAggregator()
    
    if args.collect:
        results = aggregator.collect_all()
        print(f"收集到 {len(results)} 个结果")
    
    elif args.report:
        results = aggregator.collect_all()
        report = aggregator.generate_report(results, args.report, args.output)
        print(report[:1000] + "..." if len(report) > 1000 else report)
    
    elif args.summary:
        results = aggregator.collect_all()
        summary = aggregator.get_summary(results)
        print(json.dumps(summary, indent=2, ensure_ascii=False))