# OpenClaw Multi-Agent System 🤖

> **突破单线程限制，实现真正的并行AI任务处理**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-green.svg)](https://openclaw.ai)

## 📖 项目介绍

OpenClaw Multi-Agent System 是一个基于OpenClaw平台的多智能体并行任务处理框架。它实现了**指挥官-执行者（Commander-Worker）架构**，突破OpenClaw单线程限制，让多个AI Agent同时处理不同任务，显著提升复杂项目的执行效率。

### 核心特性

- 🚀 **真正并行**: 5+ Agent同时运行，告别串行等待
- 🎯 **智能调度**: 自动任务分配与负载均衡
- 📊 **结果聚合**: 多Agent结果自动汇总整理
- 🔄 **容错机制**: 单点失败不影响整体任务
- 📝 **完整追踪**: 任务执行全过程可审计

## 🏗️ 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Commander (总指挥)                          │
│                         小e (main agent)                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  任务分解   │  │  调度决策   │  │  结果汇总   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Worker Agents (执行者)                      │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Acho 🎯    │  │  Blon 💻    │  │  Gina 🎨    │             │
│  │  产品经理   │  │  技术总监   │  │  美术总监   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  Danny 📊   │  │  Oliver 📈  │                               │
│  │  市场总监   │  │  数据总监   │                               │
│  └─────────────┘  └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Storage (共享存储)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  tasks/     │  │  results/   │  │  logs/      │             │
│  │  任务队列   │  │  结果存储   │  │  执行日志   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 通信协议

```
┌──────────┐     Spawn Task      ┌──────────┐
│Commander │ ──────────────────> │ Worker A │
└──────────┘                     └──────────┘
     │                               │
     │  Write to shared file         │ Read & Execute
     ▼                               ▼
┌─────────────────────────────────────────────┐
│        ~/.openclaw/workspace/shared_tasks/  │
│        task_[id].json                       │
└─────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

```bash
# Python 3.10+
python --version

# OpenClaw CLI
openclaw --version
```

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/openclaw-multi-agent.git
cd openclaw-multi-agent

# 安装依赖
pip install -r requirements.txt
```

### 基础使用

```python
from src.agent_spawner import AgentSpawner
from src.task_distributor import TaskDistributor
from src.result_aggregator import ResultAggregator

# 1. 初始化组件
spawner = AgentSpawner()
distributor = TaskDistributor()
aggregator = ResultAggregator()

# 2. 定义任务
tasks = [
    {"agent": "alpha", "task": "竞品分析", "priority": 1},
    {"agent": "beta", "task": "技术调研", "priority": 1},
    {"agent": "gamma", "task": "UI设计", "priority": 2},
    {"agent": "delta", "task": "市场分析", "priority": 1},
    {"agent": "omega", "task": "数据收集", "priority": 1},
]

# 3. 并行分发任务
distributor.dispatch_parallel(tasks)

# 4. 收集结果
results = aggregator.collect_all(timeout=300)
print(f"完成 {len(results)} 个任务")
```

### 命令行使用

```bash
# 启动完整工作流
python examples/seo_project_example.py

# 单独启动Agent
python -m src.agent_spawner --agent alpha --task "竞品分析"
```

## 📂 项目结构

```
openclaw-multi-agent/
├── src/                          # 核心源代码
│   ├── agent_spawner.py          # Agent生成器
│   ├── task_distributor.py       # 任务分发器
│   ├── result_aggregator.py      # 结果聚合器
│   └── communication.py          # 通信协议实现
├── examples/                     # 使用示例
│   ├── basic_example.py          # 基础示例
│   └── seo_project_example.py    # SEO项目实战
├── docs/                         # 文档
│   ├── architecture.md           # 架构设计
│   ├── best-practices.md         # 最佳实践
│   └── troubleshooting.md        # 故障排查
├── cases/                        # 实战案例
│   └── 2026-03-19-seo-project.md # 5-Agent并行SEO项目
├── tests/                        # 单元测试
├── requirements.txt              # 依赖
└── README.md                     # 本文件
```

## 💡 实战案例：SEO项目并行处理

### 项目背景

**时间**: 2026-03-19  
**任务**: 为新产品进行完整的SEO调研与优化  
**团队**: 5个Agent并行工作

### 任务分配

| Agent | 角色 | 任务 | 耗时 |
|-------|------|------|------|
| Acho 🎯 | 产品经理 | 竞品功能对比分析 | 45min |
| Blon 💻 | 技术总监 | 技术SEO审计与优化建议 | 40min |
| Gina 🎨 | 美术总监 | 着陆页视觉优化方案 | 35min |
| Danny 📊 | 市场总监 | 关键词研究与内容策略 | 50min |
| Oliver 📈 | 数据总监 | 流量数据分析与预测 | 40min |

### 效率对比

| 模式 | 预计耗时 | 实际耗时 | 效率提升 |
|------|----------|----------|----------|
| 单Agent串行 | 3.5小时 | - | - |
| 5-Agent并行 | 50分钟 | 50分钟 | **4.2x** |

### 关键成果

- ✅ 完成5个竞品深度分析
- ✅ 输出30+技术SEO优化建议
- ✅ 生成3套着陆页视觉方案
- ✅ 确定100+高价值关键词
- ✅ 建立流量预测模型

[查看完整案例 →](cases/2026-03-19-seo-project.md)

## ⚡ 技术亮点

### 1. 突破OpenClaw单线程限制

传统OpenClaw任务按顺序执行，通过`sessions_spawn`实现真正的并行执行：

```python
# 传统方式：串行执行 (总时间 = 任务1 + 任务2 + ...)
for task in tasks:
    result = execute(task)  # 等待每个任务完成

# 多Agent方式：并行执行 (总时间 ≈ 最慢的任务)
spawn_tasks = [spawn_agent(task) for task in tasks]
results = wait_all(spawn_tasks)  # 同时执行
```

### 2. 指挥官-执行者协作模式

- **Commander**: 负责思考、规划、调度，不执行具体任务
- **Workers**: 专注执行，通过共享文件异步通信

### 3. 智能任务分配

根据Agent职能和历史表现自动分配最优任务：

```python
def assign_task(task):
    agent_scores = {
        "alpha": score_for_product_task(task),
        "beta": score_for_tech_task(task),
        "gamma": score_for_design_task(task),
    }
    return max(agent_scores, key=agent_scores.get)
```

### 4. 自动结果汇总

多Agent结果自动去重、整合、格式化输出：

```python
aggregator = ResultAggregator()
aggregator.add_formatter("markdown", MarkdownFormatter())
aggregator.add_formatter("json", JSONFormatter())
final_report = aggregator.generate_report(format="markdown")
```

## 📚 文档

- [架构设计说明](docs/architecture.md) - 深入了解系统设计
- [最佳实践](docs/best-practices.md) - 高效使用指南
- [故障排查](docs/troubleshooting.md) - 常见问题解决

## 🤝 贡献指南

欢迎提交Issue和PR！请确保：

1. 代码符合PEP 8规范
2. 添加单元测试
3. 更新相关文档
4. 提交清晰的commit message

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- OpenClaw团队提供的强大平台
- 硅基军团全体成员的配合与支持

---

**Made with ❤️ by 小e and the Silicon Army**