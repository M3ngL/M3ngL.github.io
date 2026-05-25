---
layout: post
title: Claude Code显示Not logged in Run /login
category: "Other"
date: 2026-05-25
---


版本：2.1.138 (Claude Code) + kimi K2.6（kimi code）

---

## Question

````bash
export ANTHROPIC_BASE_URL="https://api.kimi.com/coding/"
export ANTHROPIC_API_KEY="sk-kimi-xxx"
export ANTHROPIC_MODEL="kimi-for-coding"
export ANTHROPIC_DEFAULT_OPUS_MODEL="kimi-for-coding"
export ANTHROPIC_DEFAULT_SONNET_MODEL="kimi-for-coding"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="kimi-for-coding"
export CLAUDE_CODE_SUBAGENT_MODEL="kimi-for-coding"
export ENABLE_TOOL_SEARCH="false"
````

第三方密钥和Base-url都配置好了，但Claude Code显示

````bash
 Not logged in · Run /login
````

## Solution

这是可能因为claude第一次初始化时，询问过是否使用本地环境变量中的 `customized api key`

若当时选择 `no`

则需要在claude code中更改设置

1. `/status`
2. config
3. 划到最底部的config字段
4. 将 `Use custom API key` 的值从 `false` 修改为 `true`

![image-20260509211356227](/pic/image-20260509211356227.png)
