---
layout: post
title: ArduPilot SITL JSON 后端连接外部仿真引擎
category: "ArduPilot"
date: 2026-11-06
---


> 版本：ArduPilot Copter-4.6.0；MuJoCo 3.16.0；Python 3.10.12；model：skydio_x2

目标：让 ArduPilot SITL 的飞控算法控制 MuJoCo 下的仿真四旋翼无人机，而两者之间的连接是通过桥接程序作为中转站来实现的。

## $Background$

ArduPilot SITL 默认使用自带的飞行动力学模型，在软件中完成飞控与物理仿真的闭环。如果希望飞控运行在 MuJoCo 等外部仿真引擎提供的动力学模型上，需要在启动 SITL 时通过 `--model json:127.0.0.1` 选择 `SIM_JSON` 后端。

但选择后端并不意味着 ArduPilot 能直接操作 MuJoCo。ArduPilot 定义了一套数据交互方式，位于 `libraries/SITL/SIM_JSON.h` ：ArduPilot 通过 UDP 输出二进制舵机 PWM 数据，并等待外部仿真引擎回传传感器 JSON。且 MuJoCo 则只负责计算物理状态，不直接理解这套协议。因此，两者之间需要一个桥接程序 Bridge，完成协议、执行器和传感器数据的转换。

本文结合 ArduPilot `SIM_JSON` 源码，以 `bridge.py` 连接 Skydio X2 MuJoCo 模型为例，说明桥接程序需要解决的四个问题：

1. 桥接程序（Bridge）接收/发送什么数据，如数据包格式的构造
2. 桥接程序如何接收/发送数据，如接收/发送端口的确定、收发顺序
3. 桥接程序需要对哪些数据，做哪些处理，如对位置信息进行坐标系变换、对pwm进行电机映射
4. 仿真引擎与 ArduPilot 的仿真步进要同步

## 要收发哪些数据

实际收发的数据只有两种：

1. 传感器 JSON 数据；该数据来源于： MuJoCo 产生传感器数据，再由 Bridge 读取并转换为 JSON 格式
2. ArduPilot 产生的二进制舵机输出包 `servos`（简称舵机包）

### 传感器 JSON 格式

`SIM_JSON.h` 的 `keytable` 要求 `timestamp`、`imu.gyro`、`imu.accel_body`、`position`、`velocity`，还需在 `attitude` 与 `quaternion` 中至少选一个。

`SIM_JSON.cpp::parse_sensors()` 按字段名查找，并用 `sscanf` 等进行转换；`recv_fdm()` 则按换行符从接收缓冲区中提取完整记录。

> `parse_sensors` 是简易解析器，不是通用 JSON 解析库，因此数据格式需要严谨

以本项目采用的 `quaternion` 为例，一条传感器 JSON 数据如下（数组值、字段层级和数值类型需与 `keytable` 的定义一一对应）：

```json
{"timestamp":0.00125,"imu":{"gyro":[0,0,0],"accel_body":[0,0,-9.81]},"position":[0,0,0],"quaternion":[1,0,0,0],"velocity":[0,0,0],"no_time_sync":0}
```

* `no_time_sync` 实际是可选项，该参数的背景： `SIM_JSON.cpp::recv_fdm()` 会用 JSON 数据的 `timestamp` 增量来推进 ArduPilot 的仿真进度；
  * 当 `no_time_sync:0` 时，将显式开启 Ardupilot 侧实际运行帧率估计和墙钟节奏同步；
  * 当 `no_time_sync:1` 时，跳过这两步。


> 墙钟节奏同步：比较**实际**经过的墙钟时间与**目标**每帧墙钟时间；如果运行得太快，就适当休眠。墙钟在这里用于控制运行节奏，不会替换 JSON 时间戳推进仿真时钟

实际发送时，Bridge 侧使用 `\n{...}\n` 定界，并进行紧凑序列化：

```python
json_bytes = ("\n" + json.dumps(msg, separators=(",", ":")) + "\n").encode("ascii")
sock.sendto(json_bytes, addr)
```

> `\n{...}\n` 定界的目的是：ArduPilot接收端函数 `recv_fdm()` 是按换行来提取完整记录

### 舵机包格式

`ArduPilot/libraries/SITL/SIM_JSON.h` 定义了默认的 16 通道包 `servo_packet_16`：

```cpp
struct servo_packet_16 {
    uint16_t magic = 18458;
    uint16_t frame_rate;
    uint32_t frame_count;
    uint16_t pwm[16];
}; // 40 Byte
```

`SIM_JSON.cpp::output_servos()` 会将 `servo_packet_16` 填入当前 `input.servos`，再通过 socket `sendto()` 发送。

也就是 ArduPilot 将按 C++ 结构体的内存布局直接发送字节（因此是二进制包），因此 Bridge 必须按发送方实际写入的格式解码。

而本地PC是小端序，16 通道包实际为 40 字节，Beidge 使用 `"<HHI16H"` 解码：

```python
SERVO_FMT = "<HHI16H"
pkt, addr = sock.recvfrom(80)
if len(pkt) != struct.calcsize(SERVO_FMT):
    continue
magic, frame_rate, frame_count, *pwm = struct.unpack(SERVO_FMT, pkt)
if magic != 18458:
    continue
```

* `pwm[0]` 是 CH1，单位 μs，实际是以微秒表示的 PWM 脉宽控制值（从这个数值到实际转速指令还有一些计算）
* `frame_rate` 是 SITL 物理模型的帧率，不是飞控主循环频率
* `frame_count` 可用于识别 SITL 重启，具体实现是 Bridge 侧来确认计数是否发生倒退，若倒退则说明 SITL 重启

## 如何收发数据

### 收发顺序：先发送 PWM，再接收 JSON

ArduPilot 命令行参数 `--model json:127.0.0.1` 将导致：

1. 在 `ArduPilot/libraries/AP_HAL_SITL/SITL_cmdline.cpp` 的模型构造表中匹配 `"JSON" → JSON::create`（使用 `strncasecmp`，大小写不敏感）
2. 然后调用 `set_interface_ports(...)`

SITL 每次更新模型时，大体经过以下调用链：

```text
AP_HAL_SITL/SITL_State.cpp:       _fdm_input_step()
  → sitl_model->update_model(input)
SITL/SIM_Aircraft.cpp:            Aircraft::update_model(input)
  → update(input)                 // SIM_JSON 模型的虚函数实现
SITL/SIM_JSON.cpp:                JSON::update(input)
  → output_servos(input)          // 先把 PWM 发给外部引擎
  → recv_fdm(input)               // 等引擎回传传感器
```

`SIM_JSON.cpp` 中决定交互方式的代码可以简化为：

```cpp
void JSON::update(const struct sitl_input &input)
{
    output_servos(input);
    recv_fdm(input);
    // 随后更新磁场、帧时间等；此处省略
}
```

由此可以发现，ArduPilot 侧是先把 PWM 发给外部引擎（即 `output_servos(input)`），后等引擎回传传感器（即 `recv_fdm(input)`）。

> `recv_fdm()` 内部有重发同一个舵机包的逻辑，因此传参有 `input`

因此桥接程序为了与ArduPilot执行顺序保持一致：首先预期收到的是执行器包，而不是预期收到来自 MuJoCo 的传感器 JSON；当 Beidge 向 ArduPilot 返回传感器数据后，`recv_fdm()` 才能继续。

因此运行时桥接程序需要先绑定 UDP 9002，SITL 随后启动，以免首包丢失。桥接程序的正常执行路径是一收一答：

```python
pkt, addr = sock.recvfrom(80)
# 校验、解码 PWM，写入 MuJoCo 模型的控制数组 data.ctrl
MuJoCo.mj_step(model, data)
sock.sendto(build_json(), addr)
```

这是一种由飞控输出驱动的锁步连接：**一次有效 PWM → 一次物理步进 → 一条传感器 JSON**。

若暂时收不到传感器，`recv_fdm()` 会等待，并约每秒重发一次 servos 包。

### 向哪个端口发送传感器 JSON

`JSON::set_interface_ports(address, port_in, port_out)` 在 `SIM_JSON.cpp` 里只设置了发送目标 `control_port = port_out`，**没有把 socket 绑定到 `port_in`**。

即使终端参数 `--sim-port-in` 默认值是 9003，但当前 `SIM_JSON` 实现并未有 `bind()` 接收来自 9003 端口号的数据。

但根据 udp 机制，在 SITL 向 `127.0.0.1:9002` 发送舵机包时，操作系统为该 socket 分配本地源端口，SITL 随后在同一个 socket 上 `recv()` 等待回复：

````cpp
SIM_JSON.cpp::recv_fdm(...){
	...
	sock.recv(...);
	...
}
````

因此 Bridge 侧可以通过 `recvfrom()` 取得实际源端口，并向该端口回发 JSON：

```python
sock.bind(("0.0.0.0", 9002))
pkt, addr = sock.recvfrom(80)
# ... 计算物理并构造 json_bytes ...
sock.sendto(json_bytes, addr)   # 回给 SITL 实际使用的源 IP:端口
```

## 哪些数据要做哪些处理

### PWM 与电机映射

> 这一步属于**具体模型适配**，不是 SIM_JSON 的通用协议

以本文为例，`skydio_x2/x2.xml` 的电机 `ctrlrange="0 13"`，因此用线性映射把 1000–2000 μs 转为 0–13 N，并按机架定义重排通道：

```python
def pwm_to_thrust(pwm_us):
    return min(13.0, max(0.0, (pwm_us - 1000.0) / 1000.0 * 13.0))

# CH1→thrust1，CH2→thrust4，CH3→thrust2，CH4→thrust3
for ch, ctrl_index in enumerate((0, 3, 1, 2)):
    data.ctrl[ctrl_index] = pwm_to_thrust(pwm[ch])
```

### MuJoCo 与 ArduPilot 的坐标变换

MuJoCo X2 模型采用 x 前、y 左、z 上的约定；而 ArduPilot 的位置/速度采用 NED 坐标系（北、东、下），IMU 量也变换到飞控预期的机体轴约定。

Bridge 使用 `R = diag(1, -1, -1)`：

```python
R_NED = np.diag([1.0, -1.0, -1.0])
position = R_NED @ (data.qpos[0:3] - home)  # 相对初始位置，单位 m
velocity = R_NED @ data.qvel[0:3]           # m/s
gyro = R_NED @ body_gyro                   # rad/s，机体系轴变换
accel = accel_sign * (R_NED @ body_linacc)  # m/s²，机体系比力
quaternion = [q[0], q[1], -q[2], -q[3]]    # [w,x,y,z]
```

*  `body_gyro`、`body_linacc`、`q` 来自 `skydio_x2/x2.xml` 的 `gyro`、`accelerometer`、`framequat` 传感器。
*  `accel_sign` 是决定加速度计值的正反，用于匹配加速度计比力约定。

## 物理步进同步

连接外部物理引擎时，需要区分 **MuJoCo 物理步进频率**与 **ArduCopter 主循环频率**

本版本的 ArduPilot 在解锁前会检查陀螺采样率，要求其不低于主循环频率 `400hz` 的 **1.8 倍**，对于“一次物理步进回传一组 IMU 数据”的桥接方式，物理步进频率也决定了可提供的陀螺采样频率。

双方按以下顺序锁步运行：

1. ArduPilot 发送舵机包，然后在 `SIM_JSON.cpp::recv_fdm()` 中等待传感器数据。
2. Bridge 收到舵机包后，调用 `MuJoCo.mj_step()` 推进一步，并用 MuJoCo 的 `data.time` 填充 JSON 的 `timestamp`。
3. Bridge 回传 JSON，ArduPilot 根据时间戳增量推进仿真时间，然后继续运行。

Bridge 显式发送 `"no_time_sync":0`，使 `SIM_JSON` 可以根据相邻时间戳的增量调整物理帧时间。Bridge 不需要按墙钟频率主动推送传感器数据；它由收到的舵机包驱动，“舵机包输出一次”对应“一次物理步进和一次 JSON 回包”。

## 数据通路总览

```text
 ArduPilot SITL SIM_JSON ── UDP 9002：二进制 PWM ──► Bridge + MuJoCo
          ▲                                               │
          │                                               ├─ PWM → 电机推力
          │                                               ├─ MuJoCo.mj_step()
          │                                               └─ 读取位姿、IMU
          └──────── UDP：传感器 JSON，回到舵机包源端口 ───────┘
```

1. **ArduPilot SITL → 桥接程序**
   通过 UDP 9002 发送二进制 PWM 包。
2. **桥接程序 → MuJoCo**
   解析 PWM，映射为无人机各电机的推力，并调用 `mj_step()` 推进物理仿真。
3. **MuJoCo → 桥接程序**
   Bridge 读取步进后的位姿、速度和 IMU 数据。
4. **桥接程序 → ArduPilot SITL**
   将数据转换到 ArduPilot 所需坐标系，构造传感器 JSON，回发到 PWM 包的源地址和端口。

## 连接验证

以下命令在仓库根目录的两个终端执行。

1. 终端一启动 Bridge：

```bash
python bridge.py
```

2. 启动 ArduPilot SITL，选择 `SIM_JSON` 后端

```bash
/path/to/arducopter -S -w \
  --model json:127.0.0.1 \
  --home 37.4,-122.08,0,0 \
  --serial0 udpclient:127.0.0.1:14550
```

* `-w` 防止旧参数覆盖 `--defaults`
* 显式指定 `--serial0` 可避免默认串口等待 GCS 连接
* 如果模型需要特定的机架、电机或传感器配置，应另外使用 `--defaults /path/to/your.parm` 加载相应参数。

桥接程序收到合法舵机包并发出传感器 JSON，同时 SITL 输出 `JSON received:`，即可初步确认数据通路已建立。这**不等于**坐标系、电机映射正确，也不代表飞控已经能够解锁或稳定飞行；这些还需要单独验证。

### Bridge.py

````python
#!/usr/bin/env python3
import json
import socket
import struct
import sys

import MuJoCo
import numpy as np


model = MuJoCo.MjModel.from_xml_path("your_model_path")
model.opt.timestep = 0.00125
data = MuJoCo.MjData(model)
home = data.qpos[:3].copy()
R = np.diag([1.0, -1.0, -1.0])


def sensor(name):
    i = MuJoCo.mj_name2id(model, MuJoCo.mjtObj.mjOBJ_SENSOR, name)
    start = model.sensor_adr[i]
    return np.array(data.sensordata[start:start + model.sensor_dim[i]])


# 用独立的仿真状态检查静置时加速度计的符号，不推进正式仿真的时间。
check = MuJoCo.MjData(model)
for _ in range(1000):
    MuJoCo.mj_step(model, check)

i = MuJoCo.mj_name2id(model, MuJoCo.mjtObj.mjOBJ_SENSOR, "body_linacc")
start = model.sensor_adr[i]
a = check.sensordata[start:start + 3]
if abs(a[2]) < 5:
    raise RuntimeError(f"invalid stationary accelerometer: {a}")
accel_sign = 1 if a[2] > 0 else -1

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 9002))
print("bridge ready udp 9002", flush=True)

count = 0
while True:
    pkt, addr = sock.recvfrom(256)
    if len(pkt) != 40:
        continue

    magic, rate, frame, *pwm = struct.unpack("<HHI16H", pkt)
    if magic != 18458:
        continue

    # CH1→thrust1，CH2→thrust4，CH3→thrust2，CH4→thrust3。
    for ch, motor in enumerate((0, 3, 1, 2)):
        data.ctrl[motor] = min(
            13.0, max(0.0, (pwm[ch] - 1000.0) / 1000.0 * 13.0)
        )

    MuJoCo.mj_step(model, data)

    q = sensor("body_quat")
    msg = {
        "timestamp": float(data.time),
        "imu": {
            "gyro": (R @ sensor("body_gyro")).tolist(),
            "accel_body": (accel_sign * R @ sensor("body_linacc")).tolist(),
        },
        "position": (R @ (data.qpos[:3] - home)).tolist(),
        "quaternion": [float(q[0]), float(q[1]), float(-q[2]), float(-q[3])],
        "velocity": (R @ data.qvel[:3]).tolist(),
        "no_time_sync": 0,
    }

    payload = ("\n" + json.dumps(msg, separators=(",", ":")) + "\n").encode("ascii")
    sock.sendto(payload, addr)  # 必须回到 SITL 发包时使用的源端口。

    count += 1
    if count == 1 or count % 800 == 0:
        print(
            f"rx_pwm={count} tx_json={count} "
            f"t={data.time:.3f} rate={rate} peer={addr}",
            flush=True,
        )
````

