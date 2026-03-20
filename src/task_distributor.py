"""
Task Distributor - 任务分发器
负责将任务智能分配给最适合的Agent并并行执行
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from agent_spawner import AgentSpawner, SpawnResult


@dataclass
class Task:
    """任务定义"""
    id: str
    type: str  # 任务类型：product/tech/design/market/data
    title: str
    description: str
    priority: int  # 1-5，数字越小优先级越高
    estimated_minutes: int
    dependencies: List[str] = None  # 依赖的任务ID列表
    context: dict = None
    assigned_agent: str = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.context is None:
            self.context = {}


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    agent_id: str
    agent_type: str
    status: str  # pending/running/completed/failed/timeout
    output_file: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: float
    result_summary: str


class TaskDistributor:
    """任务分发器 - 智能任务分配与并行调度"""
    
    # 任务类型到Agent类型的映射
    TASK_AGENT_MAPPING = {
        "product": ["alpha"],      # 产品相关 → Acho
        "tech": ["beta"],          # 技术相关 → Blon
        "design": ["gamma"],       # 设计相关 → Gina
        "market": ["delta"],       # 市场相关 → Danny
        "data": ["omega"],         # 数据相关 → Oliver
        "analysis": ["alpha", "omega"],  # 分析类 → Acho或Oliver
        "research": ["beta", "delta"],   # 调研类 → Blon或Danny
    }
    
    def __init__(self, max_workers: int = 5, shared_dir: str = None):
        """
        初始化任务分发器
        
        Args:
            max_workers: 最大并行Worker数量
            shared_dir: 共享目录路径
        """
        self.max_workers = max_workers
        self.shared_dir = Path(shared_dir or "~/.openclaw/workspace").expanduser()
        self.shared_tasks_dir = self.shared_dir / "shared_tasks"
        self.shared_results_dir = self.shared_dir / "shared_results"
        
        # 确保目录存在
        self.shared_tasks_dir.mkdir(parents=True, exist_ok=True)
        self.shared_results_dir.mkdir(parents=True, exist_ok=True)
        
        # 组件初始化
        self.spawner = AgentSpawner(str(self.shared_tasks_dir))
        
        # 状态追踪
        self.active_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.task_callbacks: Dict[str, List[Callable]] = {}
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def add_task(self, 
                 task_type: str,
                 title: str,
                 description: str,
                 priority: int = 1,
                 estimated_minutes: int = 30,
                 dependencies: List[str] = None,
                 context: dict = None) -> str:
        """
        添加单个任务到队列
        
        Args:
            task_type: 任务类型
            title: 任务标题
            description: 任务描述
            priority: 优先级（1最高）
            estimated_minutes: 预计耗时
            dependencies: 依赖的任务ID
            context: 额外上下文
            
        Returns:
            任务ID
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        task = Task(
            id=task_id,
            type=task_type,
            title=title,
            description=description,
            priority=priority,
            estimated_minutes=estimated_minutes,
            dependencies=dependencies or [],
            context=context or {}
        )
        
        self.active_tasks[task_id] = task
        self.logger.info(f"添加任务: {title} (ID: {task_id})")
        
        return task_id
    
    def add_tasks(self, tasks: List[dict]) -> List[str]:
        """
        批量添加任务
        
        Args:
            tasks: 任务配置列表
            
        Returns:
            任务ID列表
        """
        task_ids = []
        for task_config in tasks:
            task_id = self.add_task(**task_config)
            task_ids.append(task_id)
        return task_ids
    
    def assign_agent(self, task: Task) -> Optional[str]:
        """
        为任务分配最合适的Agent
        
        Args:
            task: 任务对象
            
        Returns:
            Agent类型字符串或None
        """
        candidates = self.TASK_AGENT_MAPPING.get(task.type)
        
        if not candidates:
            self.logger.warning(f"未知任务类型: {task.type}，使用默认Agent")
            return "alpha"
        
        # 简单策略：选择第一个候选
        # 进阶策略：可以检查Agent负载，选择最空闲的
        return candidates[0]
    
    def dispatch_single(self, task_id: str, wait: bool = False) -> SpawnResult:
        """
        分发单个任务
        
        Args:
            task_id: 任务ID
            wait: 是否等待完成
            
        Returns:
            SpawnResult对象
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return SpawnResult(
                success=False,
                agent_id="",
                task_id=task_id,
                message=f"任务不存在: {task_id}",
                timestamp=datetime.now().isoformat()
            )
        
        # 检查依赖
        for dep_id in task.dependencies:
            if dep_id in self.task_results:
                dep_result = self.task_results[dep_id]
                if dep_result.status != "completed":
                    return SpawnResult(
                        success=False,
                        agent_id="",
                        task_id=task_id,
                        message=f"依赖任务未完成: {dep_id}",
                        timestamp=datetime.now().isoformat()
                    )
        
        # 分配Agent
        agent_type = self.assign_agent(task)
        task.assigned_agent = agent_type
        
        # 构建交付物路径
        deliverable = f"{self.shared_results_dir}/{task_id}_result.md"
        
        # 生成Agent
        result = self.spawner.spawn(
            agent_type=agent_type,
            task_description=f"{task.title}\n\n{task.description}",
            deliverable=str(deliverable),
            timeout_minutes=task.estimated_minutes + 15,  # 增加缓冲时间
            context={
                "task_id": task_id,
                "task_type": task.type,
                **task.context
            }
        )
        
        if result.success:
            self.logger.info(f"任务 {task_id} 已分配给 {agent_type}")
            
            # 记录任务结果跟踪
            self.task_results[task_id] = TaskResult(
                task_id=task_id,
                agent_id=result.agent_id,
                agent_type=agent_type,
                status="running",
                output_file=str(deliverable),
                start_time=datetime.now().isoformat(),
                end_time=None,
                duration_seconds=0,
                result_summary=""
            )
        
        return result
    
    def dispatch_parallel(self, task_ids: Optional[List[str]] = None) -> List[SpawnResult]:
        """
        并行分发多个任务
        
        Args:
            task_ids: 要分发的任务ID列表，None表示分发所有待处理任务
            
        Returns:
            SpawnResult列表
        """
        if task_ids is None:
            task_ids = list(self.active_tasks.keys())
        
        # 按优先级排序
        sorted_tasks = sorted(
            [(tid, self.active_tasks[tid]) for tid in task_ids],
            key=lambda x: x[1].priority
        )
        
        results = []
        
        self.logger.info(f"开始并行分发 {len(sorted_tasks)} 个任务")
        start_time = time.time()
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self.dispatch_single, task_id): task_id
                for task_id, _ in sorted_tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.success:
                        self.logger.info(f"✓ 任务 {task_id} 启动成功")
                    else:
                        self.logger.error(f"✗ 任务 {task_id} 启动失败: {result.message}")
                        
                except Exception as e:
                    self.logger.error(f"✗ 任务 {task_id} 异常: {str(e)}")
                    results.append(SpawnResult(
                        success=False,
                        agent_id="",
                        task_id=task_id,
                        message=f"异常: {str(e)}",
                        timestamp=datetime.now().isoformat()
                    ))
        
        elapsed = time.time() - start_time
        self.logger.info(f"并行分发完成，耗时 {elapsed:.2f} 秒")
        
        return results
    
    def dispatch_sequential(self, task_ids: List[str]) -> List[SpawnResult]:
        """
        串行分发任务（用于有严格依赖关系的任务）
        
        Args:
            task_ids: 任务ID列表
            
        Returns:
            SpawnResult列表
        """
        results = []
        
        self.logger.info(f"开始串行分发 {len(task_ids)} 个任务")
        
        for task_id in task_ids:
            result = self.dispatch_single(task_id, wait=True)
            results.append(result)
            
            if not result.success:
                self.logger.error(f"任务 {task_id} 失败，停止后续任务")
                break
        
        return results
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        task = self.active_tasks.get(task_id)
        result = self.task_results.get(task_id)
        
        if not task:
            return None
        
        return {
            "task": asdict(task),
            "result": asdict(result) if result else None
        }
    
    def get_all_status(self) -> Dict[str, dict]:
        """获取所有任务状态"""
        return {
            task_id: self.get_task_status(task_id)
            for task_id in self.active_tasks.keys()
        }
    
    def wait_for_completion(self, task_ids: List[str] = None, 
                           timeout: int = 3600,
                           poll_interval: int = 10) -> List[TaskResult]:
        """
        等待任务完成
        
        Args:
            task_ids: 要等待的任务ID，None表示所有任务
            timeout: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
            
        Returns:
            TaskResult列表
        """
        if task_ids is None:
            task_ids = list(self.active_tasks.keys())
        
        start_time = time.time()
        completed_tasks = set()
        
        self.logger.info(f"等待 {len(task_ids)} 个任务完成...")
        
        while len(completed_tasks) < len(task_ids):
            if time.time() - start_time > timeout:
                self.logger.warning("等待超时")
                break
            
            for task_id in task_ids:
                if task_id in completed_tasks:
                    continue
                
                result = self.task_results.get(task_id)
                if result and result.status in ["completed", "failed", "timeout"]:
                    completed_tasks.add(task_id)
                    self.logger.info(f"任务 {task_id} 状态: {result.status}")
            
            if len(completed_tasks) < len(task_ids):
                time.sleep(poll_interval)
        
        return [self.task_results[tid] for tid in completed_tasks if tid in self.task_results]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        result = self.task_results.get(task_id)
        if result:
            result.status = "cancelled"
            result.end_time = datetime.now().isoformat()
            return True
        return False


# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Task Distributor CLI")
    parser.add_argument("--add", "-a", help="添加任务（JSON格式）")
    parser.add_argument("--dispatch", "-d", action="store_true", help="分发所有任务")
    parser.add_argument("--status", "-s", help="查看任务状态")
    parser.add_argument("--wait", "-w", action="store_true", help="等待完成")
    
    args = parser.parse_args()
    
    distributor = TaskDistributor()
    
    if args.add:
        task_config = json.loads(args.add)
        task_id = distributor.add_task(**task_config)
        print(f"添加任务成功: {task_id}")
    
    elif args.dispatch:
        results = distributor.dispatch_parallel()
        print(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False))
    
    elif args.status:
        status = distributor.get_task_status(args.status)
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif args.wait:
        results = distributor.wait_for_completion()
        print(f"完成 {len(results)} 个任务")