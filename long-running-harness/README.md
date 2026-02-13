# Long-Running Agent Harness

基于 Anthropic 文章 [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的智能体编排框架实现。

## 概述

长时间运行智能体面临核心挑战：必须在多个 context window 间以离散会话工作，每次新会话都无前序记忆。本框架采用 **三阶段** 流程，并在进入开发前增加 **需求审阅** 环节：

| 阶段 | Agent | 职责 |
|------|-------|------|
| **Phase 0** | Requirements Analyst | 分析并完善用户原始需求，输出 `refined_requirements.md`，**供用户审阅** |
| **Phase 1** | Initializer Agent | 用户确认后，读取审定后的 spec，创建 `feature_list.json`、`init.sh`，初始化 git |
| **Phase 2** | Coding Agent | 逐项实现 feature，用浏览器自动化验证，只修改 `passes` 字段 |

用户往往不清楚自己的需求是否完整、无歧义。Phase 0 会对需求做分析、补全与结构化，生成详细需求文档，用户审阅（可编辑）后再用 `--approved` 进入开发，避免“需求偏差”再返工。

## 核心机制

1. **feature_list.json**：功能与测试的唯一来源，禁止删除或编辑，仅允许将 `passes` 从 false 改为 true
2. **claude-progress.txt**：会话摘要与后续建议
3. **init.sh**：环境与开发服务器启动
4. **Git**：提交与回滚，保持可追溯状态

## 快速开始

### 前置要求

```bash
# 安装 Claude Code CLI
npm install -g @anthropic-ai/claude-code

# 安装 Python 依赖
pip install -r requirements.txt
```

### 环境变量

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 运行

```bash
# 1) 首次运行：根据 prompts/app_spec.txt 做需求分析与完善，生成 refined_requirements.md
python autonomous_agent_demo.py --project-dir ./my_project

# 2) 审阅 project_dir/refined_requirements.md，可按需编辑

# 3) 确认需求后，开始开发（Initializer → Coding Agent）
python autonomous_agent_demo.py --project-dir ./my_project --approved

# 之后每次运行会继续 Coding Agent 直到达到 max-iterations 或完成
python autonomous_agent_demo.py --project-dir ./my_project --max-iterations 5
```

### 自定义应用

编辑 `prompts/app_spec.txt` 描述你的**原始**需求；Phase 0 会据此生成 `refined_requirements.md`，你审阅并 `--approved` 后，Initializer 会按审定后的需求生成 `feature_list.json`。

## 目录结构

```
long-running-harness/
├── harness_config.yaml      # 框架配置（Agent 角色、失败模式、SDK 设置）
├── autonomous_agent_demo.py # 入口
├── agent.py                 # 会话逻辑与循环
├── client.py                # Claude SDK 客户端
├── progress.py              # 进度统计
├── security.py              # Bash 白名单
├── prompts.py               # Prompt 加载
├── prompts/
│   ├── requirements_refinement_prompt.md  # Phase 0：需求分析 prompt
│   ├── initializer_prompt.md
│   ├── coding_prompt.md
│   └── app_spec.txt         # 用户原始需求模板（可编辑）
└── requirements.txt
```

## 参考资料

- **文章**: [Effective harnesses for long-running agents | Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- **官方代码**: [anthropics/claude-quickstarts/autonomous-coding](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)
- **Claude Agent SDK**: [Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
