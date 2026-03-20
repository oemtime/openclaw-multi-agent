"""
Communication - 通信协议实现
定义Agent间通信的标准协议和数据格式
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import threading
import logging


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    TIMEOUT = "timeout"         # 超时
    CANCELLED = "cancelled"     # 已取消


class MessageType(Enum):
    """消息类型枚举"""
    TASK_ASSIGN = "task_assign"     # 任务分配
    TASK_UPDATE = "task_update"     # 任务更新
    TASK_COMPLETE = "task_complete" # 任务完成
    HEARTBEAT = "heartbeat"         # 心跳
    ERROR = "error"                 # 错误
    COMMAND = "command"             # 命令


@dataclass
class TaskMessage:
    """任务消息"""
    message_id: str
    message_type: MessageType
    from_agent: str
    to_agent: str
    task_id: str
    payload: dict
    timestamp: str
    priority: int = 1  # 1-5，数字越小优先级越高
    
    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "task_id": self.task_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TaskMessage':
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            task_id=data["task_id"],
            payload=data["payload"],
            timestamp=data["timestamp"],
            priority=data.get("priority", 1)
        )


@dataclass
class TaskDefinition:
    """任务定义"""
    task_id: str
    task_type: str
    title: str
    description: str
    assigned_agent: str
    deliverable: str
    deadline: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SharedFileProtocol:
    """
    共享文件通信协议
    
    基于文件系统的轻量级Agent间通信机制
    适用于OpenClaw多Agent场景
    """
    
    def __init__(self, base_dir: str = None):
        """
        初始化通信协议
        
        Args:
            base_dir: 共享目录基础路径
        """
        self.base_dir = Path(base_dir or "~/.openclaw/workspace").expanduser()
        self.messages_dir = self.base_dir / "shared_messages"
        self.tasks_dir = self.base_dir / "shared_tasks"
        
        # 创建目录
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # 消息处理器
        self.message_handlers: Dict[MessageType, List[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }
        
        # 轮询控制
        self._polling = False
        self._polling_thread: Optional[threading.Thread] = None
        
        # 日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, message: TaskMessage) -> bool:
        """
        发送消息
        
        Args:
            message: 消息对象
            
        Returns:
            是否发送成功
        """
        try:
            # 构建消息文件路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{message.to_agent}_{timestamp}_{message.message_id}.json"
            message_file = self.messages_dir / filename
            
            # 写入消息
            with open(message_file, 'w', encoding='utf-8') as f:
                json.dump(message.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"消息已发送: {message.message_id} -> {message.to_agent}")
            return True
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    def create_task_file(self, task: TaskDefinition) -> str:
        """
        创建任务文件
        
        Args:
            task: 任务定义
            
        Returns:
            任务文件路径
        """
        task_file = self.tasks_dir / f"{task.task_id}.json"
        
        task_data = {
            **asdict(task),
            "status": TaskStatus.PENDING.value,
            "started_at": None,
            "completed_at": None,
            "result": None,
            "logs": []
        }
        
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"任务文件已创建: {task.task_id}")
        return str(task_file)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: dict = None, log: str = None) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            result: 结果数据
            log: 日志条目
            
        Returns:
            是否更新成功
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        
        if not task_file.exists():
            self.logger.warning(f"任务文件不存在: {task_id}")
            return False
        
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            # 更新状态
            task_data["status"] = status.value
            
            if status == TaskStatus.RUNNING and not task_data.get("started_at"):
                task_data["started_at"] = datetime.now().isoformat()
            
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
                task_data["completed_at"] = datetime.now().isoformat()
            
            if result:
                task_data["result"] = result
            
            if log:
                task_data["logs"].append({
                    "timestamp": datetime.now().isoformat(),
                    "message": log
                })
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务数据字典或None
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        
        if not task_file.exists():
            return None
        
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"读取任务失败: {e}")
            return None
    
    def list_tasks(self, agent_id: str = None, status: TaskStatus = None) -> List[dict]:
        """
        列出任务
        
        Args:
            agent_id: 按Agent过滤
            status: 按状态过滤
            
        Returns:
            任务列表
        """
        tasks = []
        
        for task_file in self.tasks_dir.glob("*.json"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                # 过滤
                if agent_id and task_data.get("assigned_agent") != agent_id:
                    continue
                
                if status and task_data.get("status") != status.value:
                    continue
                
                tasks.append(task_data)
                
            except Exception as e:
                self.logger.warning(f"读取任务文件失败 {task_file}: {e}")
        
        return tasks
    
    def poll_messages(self, agent_id: str, 
                     interval: int = 5,
                     callback: Callable[[TaskMessage], None] = None) -> None:
        """
        轮询消息（阻塞方法）
        
        Args:
            agent_id: Agent ID
            interval: 轮询间隔（秒）
            callback: 消息回调函数
        """
        self.logger.info(f"开始轮询消息: {agent_id}")
        
        while self._polling:
            messages = self._read_messages_for_agent(agent_id)
            
            for message in messages:
                if callback:
                    callback(message)
                
                # 触发注册的处理器
                for handler in self.message_handlers.get(message.message_type, []):
                    try:
                        handler(message)
                    except Exception as e:
                        self.logger.error(f"消息处理器错误: {e}")
                
                # 删除已处理的消息
                self._delete_message(message.message_id)
            
            time.sleep(interval)
    
    def start_polling(self, agent_id: str, interval: int = 5,
                     callback: Callable[[TaskMessage], None] = None):
        """
        启动后台轮询
        
        Args:
            agent_id: Agent ID
            interval: 轮询间隔
            callback: 回调函数
        """
        self._polling = True
        self._polling_thread = threading.Thread(
            target=self.poll_messages,
            args=(agent_id, interval, callback),
            daemon=True
        )
        self._polling_thread.start()
    
    def stop_polling(self):
        """停止轮询"""
        self._polling = False
        if self._polling_thread:
            self._polling_thread.join(timeout=5)
    
    def register_handler(self, message_type: MessageType, 
                        handler: Callable[[TaskMessage], None]):
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[message_type].append(handler)
    
    def _read_messages_for_agent(self, agent_id: str) -> List[TaskMessage]:
        """读取指定Agent的消息"""
        messages = []
        
        # 查找匹配的消息文件
        for message_file in self.messages_dir.glob(f"{agent_id}_*.json"):
            try:
                with open(message_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    messages.append(TaskMessage.from_dict(data))
            except Exception as e:
                self.logger.warning(f"读取消息失败 {message_file}: {e}")
        
        # 按优先级和时间排序
        messages.sort(key=lambda m: (m.priority, m.timestamp))
        
        return messages
    
    def _delete_message(self, message_id: str):
        """删除消息文件"""
        for message_file in self.messages_dir.glob(f"*_{message_id}.json"):
            try:
                message_file.unlink()
            except Exception as e:
                self.logger.warning(f"删除消息失败: {e}")
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        清理过期文件
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        for directory in [self.messages_dir, self.tasks_dir]:
            for file_path in directory.glob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff:
                        file_path.unlink()
                        self.logger.debug(f"清理过期文件: {file_path}")
                except Exception as e:
                    self.logger.warning(f"清理文件失败 {file_path}: {e}")


# 便捷函数
def create_task_message(
    from_agent: str,
    to_agent: str,
    task_id: str,
    message_type: MessageType,
    payload: dict,
    priority: int = 1
) -> TaskMessage:
    """
    创建任务消息
    
    Args:
        from_agent: 发送方
        to_agent: 接收方
        task_id: 任务ID
        message_type: 消息类型
        payload: 消息内容
        priority: 优先级
        
    Returns:
        TaskMessage对象
    """
    return TaskMessage(
        message_id=f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}",
        message_type=message_type,
        from_agent=from_agent,
        to_agent=to_agent,
        task_id=task_id,
        payload=payload,
        timestamp=datetime.now().isoformat(),
        priority=priority
    )


if __name__ == "__main__":
    # 测试代码
    protocol = SharedFileProtocol()
    
    # 创建测试任务
    task = TaskDefinition(
        task_id="test_001",
        task_type="test",
        title="测试任务",
        description="这是一个测试任务",
        assigned_agent="alpha",
        deliverable="test_result.md"
    )
    
    task_file = protocol.create_task_file(task)
    print(f"任务文件: {task_file}")
    
    # 发送测试消息
    message = create_task_message(
        from_agent="main",
        to_agent="alpha",
        task_id="test_001",
        message_type=MessageType.TASK_ASSIGN,
        payload={"action": "start"}
    )
    
    success = protocol.send_message(message)
    print(f"消息发送: {'成功' if success else '失败'}")