# 指定特工调度配置经验

> 日期：2026-03-20
> 配置者：宁非（老板）+ 小e
> 场景：OpenClaw 多Agent并行任务调度

---

## 🎯 问题背景

`sessions_spawn` 调用指定 `agentId` 时返回错误：
```
status: "forbidden"
error: "agentId is not allowed for sessions_spawn (allowed: none)"
```

## ✅ 解决方案

### 步骤1：确认Agents已配置

运行以下命令检查：
```bash
openclaw agents list
```

应看到类似输出：
```
Agents:
- alpha-bot (default) - 🎯 Acho
- beta-bot - 💻 Blon
- gamma-bot - 🎨 Gina
- delta-bot - 📊 Danny
- omega-bot - 📈 Oliver
- xiaoe-bot - 🤖 小e
```

### 步骤2：配置 allowedAgents（关键）

**方式A：通过Dashboard配置（推荐）**

在OpenClaw Dashboard中找到 **Agents** 或 **Subagents** 设置，添加 `allowedAgents` 列表。

**方式B：手动编辑配置文件**

编辑 `~/.openclaw/openclaw.json`，在 `agents.defaults` 下添加：

```json
{
  "agents": {
    "defaults": {
      "allowedAgents": [
        "alpha-bot",
        "beta-bot",
        "gamma-bot",
        "delta-bot",
        "omega-bot"
      ]
    }
  }
}
```

**注意**：不同版本的OpenClaw配置键可能不同，如果上述配置报错，请使用Dashboard方式。

### 步骤3：重启Gateway

```bash
openclaw gateway restart
```

### 步骤4：测试调度

```javascript
await sessions_spawn({
    agentId: "beta-bot",  // 指定特工
    task: "测试任务",
    mode: "run"
});
```

成功标志：
```
status: "accepted"
childSessionKey: "agent:beta-bot:subagent:xxxxx"
```

---

## 💡 关键发现

1. **不指定 agentId 时，调度始终可用**（通用子代理）
2. **指定 agentId 需要额外配置 allowedAgents**
3. **配置生效需要重启 Gateway**
4. **Dashboard配置比手动编辑配置文件更可靠**

---

## 🚀 使用示例

### 并行调度5个特工

```javascript
// 调度 Acho (产品经理)
await sessions_spawn({
    agentId: "alpha-bot",
    task: "产品需求分析...",
    mode: "run"
});

// 调度 Blon (技术总监)
await sessions_spawn({
    agentId: "beta-bot",
    task: "技术方案设计...",
    mode: "run"
});

// 调度 Gina (美术总监)
await sessions_spawn({
    agentId: "gamma-bot",
    task: "UI设计方案...",
    mode: "run"
});

// 调度 Danny (市场总监)
await sessions_spawn({
    agentId: "delta-bot",
    task: "市场分析报告...",
    mode: "run"
});

// 调度 Oliver (数据分析师)
await sessions_spawn({
    agentId: "omega-bot",
    task: "数据分析...",
    mode: "run"
});

// 等待所有结果自动推送
await sessions_yield();
```

---

## 📋 故障排除

| 问题 | 解决方案 |
|------|---------|
| `agentId is not allowed` | 检查Dashboard配置或手动添加allowedAgents |
| `Config invalid` | 检查JSON格式，确保无语法错误 |
| 重启后仍不生效 | 检查配置文件路径是否正确 |
| 通用子代理可用但指定不行 | allowedAgents配置未生效，尝试Dashboard配置 |

---

## 🎉 成功案例

2026-03-20，成功配置后并行执行5个任务：
- 🎯 Acho - GEO项目评估
- 📈 Oliver - Agent学习笔记
- 📊 Danny - SEO文件夹整理
- 💻 Blon - GitHub Skills整理
- 🎨 Gina - 全面测试

全部成功返回结果，实现真正的**硅基军团并行作战**！

---

**贡献者**：宁非（配置）+ 小e（整理）
**日期**：2026-03-20
