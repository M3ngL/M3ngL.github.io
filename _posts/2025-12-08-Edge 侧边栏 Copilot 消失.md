---
layout: post
title: Edge 侧边栏 Copilot 消失
category: "Other"
date: 2025-12-08
---


> 本地 edge 版本：142.0.3595.94 (正式版本) (64 位)

浏览器URL查询版本

````
edge://version
````

## Approach

关闭 Edge 浏览器

![image-20251208195023231](/pic/image-20251208195023231.png)

文件资源管理器访问

````bash
%APPDATA%\..\Local\Microsoft\Edge\User Data
````

找到并打开该文件夹下的 `Local State` 文件，

![image-20251208194336943](/pic/image-20251208194336943.png)

修改该文件中字段 `variations_country` 的值为 `US`

> 该字段在国内一般为 `CN`

![image-20251208194417188](/pic/image-20251208194417188.png)

## Reference

[解决新版Edge浏览器右上角不显示Copilot图标的问题 - 知乎](https://zhuanlan.zhihu.com/p/673914163)