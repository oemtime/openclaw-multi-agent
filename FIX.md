# 修复记录 - 多Agent并行功能

## 问题描述
**症状**: 多Agent系统无法真正实现并行执行，任务按顺序串行处理。

**根本原因**: `agent_spawner.py` 中的 `spawn()` 方法只是创建了任务文件（JSON），并没有真正调用 OpenClaw 的 `sessions_spawn` API 来启动并行的 Agent 会话。

```python
# 修复前 - 只是伪代码
def _build_spawn_command(self, agent_type: str, task_id: str) -> str:
    """
    构建spawn命令
    注意：这是伪代码，实际应使用OpenClaw的sessions_spawn API  # <-- 问题在这里！
    """
    return f"..."
```

## 修复内容

### 1. 添加真正的 Spawn 执行 (`agent_spawner.py`)

新增 `_execute_spawn()` 方法，使用 `subprocess.Popen` 真正调用 OpenClaw CLI：

```python
def _execute_spawn(self, agent_type: str, task_id: str, task_description: str, timeout_minutes: int = 60) -> bool:
    """执行真正的OpenClaw spawn命令"""
    try:
        agent_config = self.get_agent_config(agent_type)
        role_prompt = f"""你是{agent_config.name}，担任{agent_config.role}。
        
你的任务是：{task_description}
..."""

        # 构建openclaw CLI命令
        cmd = [
            "openclaw", "sessions_spawn",
            "--task", role_prompt,
            "--runtime", "subagent",
            "--mode", "run",
            "--label", f"{agent_type}_{task_id}",
            "--timeout", str(timeout_minutes * 60)
        ]
        
        # 在后台执行，不等待完成（实现真正的并行）
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return True
    except Exception as e:
        print(f"执行spawn命令失败: {e}")
        return False
```

### 2. 修改 `spawn()` 方法调用真正的执行

```python
def spawn(self, ...):
    # ... 创建任务文件 ...
    
    # 真正执行spawn命令（修复前只是返回注释）
    spawn_success = self._execute_spawn(agent_type, task_id, task_description, timeout_minutes)
    
    if not spawn_success:
        return SpawnResult(success=False, ...)
    
    return SpawnResult(success=True, ...)
```

### 3. 增强 `spawn_batch()` 实现真正并行

```python
def spawn_batch(self, tasks: List[dict], parallel: bool = True) -> List[SpawnResult]:
    if not parallel:
        # 串行执行...
    
    # 并行执行 - 使用线程池同时启动多个Agent
    results = [None] * len(tasks)
    threads = []
    
    def spawn_task(index: int, task: dict):
        results[index] = self.spawn(...)
    
    # 启动所有线程
    for i, task in enumerate(tasks):
        thread = threading.Thread(target=spawn_task, args=(i, task))
        threads.append(thread)
        thread.start()
    
    # 等待所有完成
    for thread in threads:
        thread.join()
    
    return results
```

## 验证方法

运行测试脚本：

```bash
cd /path/to/openclaw-multi-agent
python test_fix.py
```

预期输出：
```
==================================================
OpenClaw 多Agent并行系统 - 修复测试
==================================================
🧪 测试单个Agent spawn...
  结果: ✅ 成功
  Agent ID: alpha_xxx
  Task ID: task_xxx
🧪 测试并行批量spawn...
  结果: 3/3 个成功
  耗时: 0.5 秒（3个任务几乎同时启动）
🧪 测试任务分发器...
  分发结果: 3/3 个成功
  总耗时: 0.8 秒
==================================================
✅ 所有测试通过！并行功能已修复。
==================================================
```

## 使用示例

### 基础用法 - 并行启动多个Agent

```python
from src.agent_spawner import AgentSpawner

spawner = AgentSpawner()

# 并行启动3个Agent
tasks = [
    {"agent": "alpha", "description": "竞品分析", "deliverable": "analysis.md"},
    {"agent": "beta", "description": "技术调研", "deliverable": "tech.md"},
    {"agent": "gamma", "description": "UI设计", "deliverable": "design.md"},
]

# parallel=True 表示真正并行执行
results = spawner.spawn_batch(tasks, parallel=True)
```

### 高级用法 - 任务分发器

```python
from src.task_distributor import TaskDistributor
from src.result_aggregator import ResultAggregator

distributor = TaskDistributor(max_workers=5)
aggregator = ResultAggregator()

# 添加任务
distributor.add_task(
    task_type="product",
    title="竞品分析",
    description="分析主要竞品功能",
    priority=1
)

# 并行分发（同时启动所有Agent）
results = distributor.dispatch_parallel()

# 等待完成并收集结果
task_results = distributor.wait_for_completion(timeout=3600)

# 生成报告
report = aggregator.generate_report(format="markdown", output_file="report.md")
```

## 架构流程

```
┌─────────────────┐
│   Commander     │  (主控Agent)
│   (你的代码)     │
└────────┬────────┘
         │ 1. 调用 spawn_batch(parallel=True)
         ▼
┌─────────────────────────────────────────┐
│  Thread Pool (线程池)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Thread1 │ │ Thread2 │ │ Thread3 │   │  <- 同时启动
│  └────┬────┘ └────┬────┘ └────┬────┘   │
└───────┼───────────┼───────────┼────────┘
        │           │           │
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ subprocess.Popen() │           │
   │ (openclaw sessions_spawn)      │
   └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Worker1 │ │ Worker2 │ │ Worker3 │  <- 真正并行的Agent进程
   │ (Alpha) │ │ (Beta)  │ │ (Gamma) │
   └─────────┘ └─────────┘ └─────────┘
```

## 注意事项

1. **环境要求**: 需要安装 OpenClaw CLI 并正确配置
2. **资源限制**: 同时启动过多 Agent 可能导致系统资源紧张，建议 `max_workers` 设置为 3-5
3. **超时设置**: 每个任务可以单独设置超时时间
4. **结果收集**: Worker Agent 需要正确更新任务状态文件以便 Commander 收集结果

## 修复提交

```bash
git add .
git commit -m "fix: 实现真正的多Agent并行执行

- 添加 _execute_spawn() 真正调用 openclaw sessions_spawn
- 使用 subprocess.Popen + start_new_session 实现后台并行
- 增强 spawn_batch() 使用线程池同时启动多个Agent
- 添加测试脚本验证并行功能

Fixes #1"
```
