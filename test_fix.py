#!/usr/bin/env python3
"""
修复测试 - 验证多Agent并行功能
"""
import sys
sys.path.insert(0, 'src')

from agent_spawner import AgentSpawner
from task_distributor import TaskDistributor
from result_aggregator import ResultAggregator

def test_spawn():
    """测试单个Agent spawn"""
    print("🧪 测试单个Agent spawn...")
    spawner = AgentSpawner()
    
    result = spawner.spawn(
        agent_type="alpha",
        task_description="分析竞品功能对比",
        deliverable="competitor_analysis.md",
        timeout_minutes=30
    )
    
    print(f"  结果: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"  Agent ID: {result.agent_id}")
    print(f"  Task ID: {result.task_id}")
    print(f"  消息: {result.message}")
    return result.success

def test_parallel_spawn():
    """测试并行批量spawn"""
    print("\n🧪 测试并行批量spawn...")
    spawner = AgentSpawner()
    
    tasks = [
        {"agent": "alpha", "description": "竞品分析", "deliverable": "analysis.md", "timeout": 30},
        {"agent": "beta", "description": "技术调研", "deliverable": "tech_research.md", "timeout": 30},
        {"agent": "gamma", "description": "UI设计", "deliverable": "design.md", "timeout": 30},
    ]
    
    import time
    start = time.time()
    results = spawner.spawn_batch(tasks, parallel=True)
    elapsed = time.time() - start
    
    success_count = sum(1 for r in results if r.success)
    print(f"  结果: {success_count}/{len(results)} 个成功")
    print(f"  耗时: {elapsed:.2f} 秒")
    
    for r in results:
        print(f"    - {r.agent_id}: {'✅' if r.success else '❌'} {r.message}")
    
    return success_count == len(results)

def test_task_distributor():
    """测试任务分发器"""
    print("\n🧪 测试任务分发器...")
    distributor = TaskDistributor(max_workers=5)
    
    # 添加任务
    task_ids = distributor.add_tasks([
        {"task_type": "product", "title": "竞品分析", "description": "分析主要竞品功能", "priority": 1},
        {"task_type": "tech", "title": "技术调研", "description": "调研技术方案", "priority": 1},
        {"task_type": "design", "title": "UI设计", "description": "设计界面原型", "priority": 2},
    ])
    
    print(f"  添加了 {len(task_ids)} 个任务")
    
    # 并行分发
    import time
    start = time.time()
    results = distributor.dispatch_parallel()
    elapsed = time.time() - start
    
    success_count = sum(1 for r in results if r.success)
    print(f"  分发结果: {success_count}/{len(results)} 个成功")
    print(f"  总耗时: {elapsed:.2f} 秒")
    
    return success_count == len(results)

if __name__ == "__main__":
    print("=" * 50)
    print("OpenClaw 多Agent并行系统 - 修复测试")
    print("=" * 50)
    
    all_passed = True
    
    # 运行测试
    all_passed &= test_spawn()
    all_passed &= test_parallel_spawn()
    all_passed &= test_task_distributor()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有测试通过！并行功能已修复。")
    else:
        print("❌ 部分测试失败，请检查日志。")
    print("=" * 50)
