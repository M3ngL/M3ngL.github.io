---
layout: post
title: ArduPilot 获取开销信息
category: "ArduPilot"
date: 2025-09-10
---


## Method

### ArduPilot Log

ArduPilot 的日志字段 `PM`，即`Performance Monitoring`日志消息提供了详细的性能指标，可直接反映交叉编译固件的性能开销

**启用条件**

需要将 ArduPilot 的参数 `Bitmask` 设置为启用`System Performance`

如果要在硬件中专门测试开销，而不解锁油门或者实际飞行，则将参数 `LOG `值设置为1

* 在Mission Planner中设置参数值（但每次编译之后都需要重新设置）
* 交叉编译之前将该参数的默认值修改为1，位于`./libraries/AP_Logger/AP_Logger.cpp`，搜索`_DISARMED`

**具体字段**

| FIELD | DESCRIPTION                                                  |
| ----- | ------------------------------------------------------------ |
| NLon  | 长时间运行的主循环的数量（即，根据SCHED_LOOP_RATE - ex，循环的时间比应该的时间长20%以上）。3 ms（400 Hz速率） |
| NLoop | 显示自上次PM消息以来的循环总数。这允许您计算运行缓慢的循环的百分比（不应高于15%）。注意，该值将取决于自动驾驶仪时钟速度 |
| MaxT  | 自上次PM消息以来任何循环所用的最长时间。这不应超过调度器循环周期的120%，但在电机处于待命状态的时间间隔内会高得多 |
| Mem   | 可用内存（字节）                                             |
| Load  | 使用CPU时计划程序循环周期的百分比（乘以10）                  |

常用的字段即 `Mem` 以及 `Load`，将该日志字段导出后根据飞控运行时间`TimeUS`作为横轴，`Mem` 或 `Load`作为纵轴即可绘制折线图，如图

![load_info](/pic/load_info.png)

### QGC Mavlink检测

使用QGC连接飞控（SITL/开发板）时，通过`Analyze Tools` -> `MAVLink检测`

可以看到 Mavlink检测的相关信息，如`SYS_STATUS, MEMINFO`等等，甚至能实时绘制数据折线图

![Snipaste_2025-09-08_20-50-09](/pic/Snipaste_2025-09-08_20-50-09.png)

但不能直接通过QGC导出这些数据，只能通过日志单独导出这些值

而QGC字段的 `SYS_STATUS` 等价于ArduPilot Log中的 `log_Performance` 结构体，记录点位于`libraries/AP_Scheduler/AP_Scheduler.cpp`

## Reference

https://ardupilot.org/copter/docs/common-downloading-and-analyzing-data-logs-in-mission-planner.html