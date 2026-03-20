"""
Agent Spawner - Agent生成器
负责创建和管理Worker Agent的生命周期
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    role: str
    emoji: str
    workspace: str
    skills: List[str]
    max_tasks: int = 3
    priority: int = 1


@dataclass
class SpawnResult:
    """生成结果"""
    success: bool
    agent_id: str
    task_id: str
    message: str
    timestamp: str


class AgentSpawner:
    """Agent生成器 - 负责spawn新的Worker Agent"""
    
    # 预定义的Agent配置
    AGENT_DEFINITIONS = {
        "alpha": AgentConfig(
            name="Acho",
            role="产品经理",
            emoji="🎯",
            workspace="~/.openclaw/workspace/alpha/",
            skills=["竞品分析", "需求梳理", "产品规划", "PRD撰写"],
            priority=1
        ),
        "beta": AgentConfig(
            name="Blon",
            role="技术总监",
            emoji="💻",
            workspace="~/.openclaw/workspace/beta/",
            skills=["技术调研", "架构设计", "代码审查", "爬虫开发"],
            priority=1
        ),
        "gamma": AgentConfig(
            name="Gina",
            role="美术总监",
            emoji="🎨",
            workspace="~/.openclaw/workspace/gamma/",
            skills=["UI设计", "视觉设计", "封面制作", "排版优化"],
            priority=2
        ),
        "delta": AgentConfig(
            name="Danny",
            role="市场总监",
            emoji="📊",
            workspace="~/.openclaw/workspace/delta/",
            skills=["市场分析", "竞品调研", "热点追踪", "内容选题"],
            priority=1
        ),
        "omega": AgentConfig(
            name="Oliver",
            role="数据总监",
            emoji="📈",
            workspace="~/.openclaw/workspace/omega/",
            skills=["数据分析", "报表制作", "ROI计算", "效果追踪"],
            priority=1
        ),
    }
    
    def __init__(self, shared_tasks_dir: str = None):
        """
        初始化Agent生成器
        
        Args:
            shared_tasks_dir: 共享任务目录路径
        """
        self.shared_tasks_dir = Path(shared_tasks_dir or 
            "~/.openclaw/workspace/shared_tasks").expanduser()
        self.shared_tasks_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_agents: Dict[str, dict] = {}
        self.spawn_history: List[dict] = []
    
    def get_agent_config(self, agent_type: str) -> Optional[AgentConfig]:
        """
        获取Agent配置
        
        Args:
            agent_type: Agent类型 (alpha/beta/gamma/delta/omega)
            
        Returns:
            AgentConfig对象或None
        """
        return self.AGENT_DEFINITIONS.get(agent_type)
    
    def spawn(self, 
              agent_type: str, 
              task_description: str,
              deliverable: str,
              timeout_minutes: int = 60,
              context: dict = None) -> SpawnResult:
        """
        生成(spawn)一个新的Agent任务
        
        Args:
            agent_type: Agent类型
            task_description: 任务描述
            deliverable: 交付物文件名
            timeout_minutes: 超时时间（分钟）
            context: 额外上下文信息
            
        Returns:
            SpawnResult对象
        """
        agent_config = self.get_agent_config(agent_type)
        if not agent_config:
            return SpawnResult(
                success=False,
                agent_id="",
                task_id="",
                message=f"未知的Agent类型: {agent_type}",
                timestamp=datetime.now().isoformat()
            )
        
        # 生成唯一ID
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        
        # 创建任务文件
        task_data = {
            "task_id": task_id,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "agent_name": agent_config.name,
            "agent_role": agent_config.role,
            "status": "pending",
            "title": f"{agent_config.emoji} {agent_config.name} - {task_description[:50]}",
            "description": task_description,
            "deliverable": deliverable,
            "timeout_minutes": timeout_minutes,
            "context": context or {},
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None
        }
        
        try:
            # 写入任务文件
            task_file = self.shared_tasks_dir / f"{task_id}.json"
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
            
            # 记录活跃Agent
            self.active_agents[agent_id] = {
                "task_id": task_id,
                "config": asdict(agent_config),
                "started_at": datetime.now().isoformat()
            }
            
            # 记录历史
            self.spawn_history.append({
                "agent_id": agent_id,
                "task_id": task_id,
                "agent_type": agent_type,
                "timestamp": datetime.now().isoformat()
            })
            
            # 实际spawn命令（OpenClaw sessions_spawn）
            spawn_command = self._build_spawn_command(agent_type, task_id)
            
            return SpawnResult(
                success=True,
                agent_id=agent_id,
                task_id=task_id,
                message=f"成功生成Agent {agent_config.name}，任务ID: {task_id}",
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return SpawnResult(
                success=False,
                agent_id=agent_id,
                task_id=task_id,
                message=f"生成失败: {str(e)}",
                timestamp=datetime.now().isoformat()
            )
    
    def spawn_batch(self, tasks: List[dict]) -> List[SpawnResult]:
        """
        批量生成Agent任务
        
        Args:
            tasks: 任务列表，每项包含agent_type, description等
            
        Returns:
            SpawnResult列表
        """
        results = []
        for task in tasks:
            result = self.spawn(
                agent_type=task["agent"],
                task_description=task["description"],
                deliverable=task.get("deliverable", "result.md"),
                timeout_minutes=task.get("timeout", 60),
                context=task.get("context")
            )
            results.append(result)
        return results
    
    def _build_spawn_command(self, agent_type: str, task_id: str) -> str:
        """
        构建spawn命令
        
        注意：这是伪代码，实际应使用OpenClaw的sessions_spawn API
        """
        return f"""
# OpenClaw sessions_spawn 命令示例
openclaw sessions_spawn \
    --agent {agent_type} \
    --task {task_id} \
    --context "~/.openclaw/workspace/shared_tasks/{task_id}.json"
"""
    
    def get_active_agents(self) -> Dict[str, dict]:
        """获取当前活跃的Agent列表"""
        return self.active_agents.copy()
    
    def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """获取指定Agent的状态"""
        agent_info = self.active_agents.get(agent_id)
        if not agent_info:
            return None
        
        task_file = self.shared_tasks_dir / f"{agent_info['task_id']}.json"
        if task_file.exists():
            with open(task_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def terminate_agent(self, agent_id: str) -> bool:
        """
        终止指定的Agent任务
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否成功终止
        """
        if agent_id not in self.active_agents:
            return False
        
        agent_info = self.active_agents[agent_id]
        task_file = self.shared_tasks_dir / f"{agent_info['task_id']}.json"
        
        if task_file.exists():
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            task_data["status"] = "terminated"
            task_data["completed_at"] = datetime.now().isoformat()
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
        
        del self.active_agents[agent_id]
        return True
    
    def list_all_agents(self) -> List[dict]:
        """列出所有可用的Agent类型"""
        return [
            {
                "type": key,
                **asdict(config)
            }
            for key, config in self.AGENT_DEFINITIONS.items()
        ]


# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Spawner CLI")
    parser.add_argument("--agent", "-a", required=True, help="Agent类型 (alpha/beta/gamma/delta/omega)")
    parser.add_argument("--task", "-t", required=True, help="任务描述")
    parser.add_argument("--deliverable", "-d", default="result.md", help="交付物文件名")
    parser.add_argument("--timeout", type=int, default=60, help="超时时间（分钟）")
    
    args = parser.parse_args()
    
    spawner = AgentSpawner()
    result = spawner.spawn(
        agent_type=args.agent,
        task_description=args.task,
        deliverable=args.deliverable,
        timeout_minutes=args.timeout
    )
    
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))