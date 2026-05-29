---
layout: post
title: Claude Code设置@引用提示无视.gitignore规则
category: "Other"
date: 2026-05-29
---


版本：Claude Code V2.1.138

## Question

Claude code 运行在某一项目中，若该项目中有 `.gitignore` 规则将某些文件/文件夹排除在版本管理之外，那么在 claude code 使用过程中想要使用 `@` 引用这些文件时，不会出现自动提示（但claude code似乎能正常读取这些文件，只是自动提示不再生效）

![image-20260529101425594](/pic/image-20260529101425594.png)

## Solution

在claude code的设置文件 `settings.json` 或者 `./.claude/settings.local.json` 中写入

````json
{
	...
	"respectGitignore": false,
	...
}
````

设置后， `@` 将自动提示和输入框字符串相匹配的文件路径

![image-20260529101402932](/pic/image-20260529101402932.png)

## Reference

https://github.com/anthropics/claude-code/issues/5105#issuecomment-3712861033