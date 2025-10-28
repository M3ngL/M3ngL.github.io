---
layout: post
title: Debugging with GDB in ArduPilot SITL
category: "ArduPilot"
date: 2025-10-28
---


环境：WSL Ubuntu 20.04.6 LTS，ArduPilot V4.6.0-dev

## Local debug templates

* **终端1：**

````bash
cd ./build/sitl/bin && gdb --args ./arducopter -S --model + --speedup 1 --defaults ../../../Tools/autotest/default_params/copter.parm -I0
````

* **终端2：**

````bash
mavproxy.py --master tcp:127.0.0.1:5760 --sitl 127.0.0.1:5501 --out 172.20.16.1:14550 --out 172.20.16.1:14551 --map --console
````

> `--out` 参数后跟着的是 WSL 的网关地址，即 windows 物理机暴露给 WSL 的IP地址，便于连接Windows上运行的地面站软件
>
> 也可以设置为 `127.0.0.1:xxx`

在终端1打上断点 breakpoint 后，输入 `r` 运行程序，此时终端1和终端2的进程将自动关联

![image-20251028161834736](/pic/image-20251028161834736.png)

ArduPilot 内许多函数都是在 `arm throttle` 甚至`takeoff` 后才会运行断点，因此在终端2输入mavlink指令

````bash
STABILIZE> mode guided
GUIDED> arm throttle
````

运行后，终端1界面将发生改变，命中断点

![image-20251028162045191](/pic/image-20251028162045191.png)

之后就可以正常使用gdb调试了

> 若是调试过程中不确定是否命中断点，比如 ArduPilot 主进程无法切换到 gdb 指令界面，可以尝试退出运行的进程主循环后，验证断点是否命中
>
> ````bash
> info breakpoints
> ````

## Debug case

**Logging IMU Gyro Data溯源**

已知 IMU 日志记录的代码位置，位于 `AP_InertialSensor::Write_IMU_instance`，该函数将根据传入的IMU实例进行日志记录

目标：查询该函数写入的 gyro 数据是从哪里获取的

1. **使用 gdb 运行 ArduPilot 与 Mavlink**

终端1，写入断点 `b AP_InertialSensor::Write_IMU_instance`，等待进程命中断点

````bash
Thread 1 "arducopter" hit Breakpoint 1, AP_InertialSensor::Write_IMU_instance (this=0x555555aa9b08 <copter+3304>, time_us=196365589, imu_instance=0 '\000') at ../../libraries/AP_InertialSensor/AP_InertialSensor_Logging.cpp:45
45      {
(gdb) 
````

终端2，运行Mavlink指令使得 ArduPilot 解锁油门

````
STABILIZE> mode guided
GUIDED> arm throttle
````

2. **进入`Write_IMU_instance`函数内部，找到该函数内的 gyro 来源**

````bash
(gdb) n
46          const Vector3f &gyro = get_gyro(imu_instance)
(gdb) s
AP_InertialSensor::get_gyro (this=0x555555aa9b08 <copter+3304>, i=0 '\000') at ../../libraries/AP_InertialSensor/AP_InertialSensor.h:112
112         const Vector3f     &get_gyro(uint8_t i) const { return _gyro[i]; }
````

3. **继续跟踪 `_gyro[i]` 的数据来源**

````bash
(gdb) print &_gyro
$4 = (Vector3f (*)[3]) 0x555555aaa1bc <copter+5020>
(gdb) watch -location _gyro[0]
Hardware watchpoint 3: -location _gyro[0]
````

4. **运行进程直到命中 ` watchpoint`，发现 `_gyro[0]` 数据来源于 `AP_InertialSensor_Backend::_publish_gyro`，打上断点**

````bash
(gdb) c
Continuing.

Thread 1 "arducopter" hit Hardware watchpoint 3: -location _gyro[0]

Old value = {x = 0.00281183701, y = 0.0027849779, z = 0.00280517712}
New value = {x = 0.00282828999, y = 0.002785936, z = 0.00280517712}
0x000055555596ba24 in AP_InertialSensor_Backend::_publish_gyro (this=0x555555b5cd00, instance=0 '\000', gyro=...) at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:172
172         _imu._gyro[instance] = gyro;
(gdb) b AP_InertialSensor_Backend::_publish_gyro
Breakpoint 4 at 0x55555596b9d9: file ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp, line 169.
````

5. **命中`_publish_gyro`断点，由于gyro是形参传入的，因此查询函数调用栈，发现有更新gyro，没有直接生成gyro数据的函数，对这些函数进行逐个断点查询**

````bash
(gdb) c
Continuing.

Thread 1 "arducopter" hit Breakpoint 4, AP_InertialSensor_Backend::_publish_gyro (this=0x555555b5cea0, instance=1 '\001', gyro=...) at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:169
169         if (has_been_killed(instance)) {
(gdb) bt
#0  AP_InertialSensor_Backend::_publish_gyro (this=0x555555b5cea0, instance=1 '\001', gyro=...)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:169
#1  0x000055555596d502 in AP_InertialSensor_Backend::update_gyro (this=0x555555b5cea0, instance=1 '\001')
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:788
#2  0x00005555558f0240 in AP_InertialSensor_SITL::update (this=0x555555b5cea0)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_SITL.cpp:387
#3  0x000055555565bf39 in AP_InertialSensor::update (this=0x555555aa9b08 <copter+3304>)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor.cpp:1906
#4  0x00005555555c6cbd in Functor<void>::method_wrapper<AP_InertialSensor, &AP_InertialSensor::update> (
    obj=0x555555aa9b08 <copter+3304>) at ../../libraries/AP_HAL/utility/functor.h:88
#5  0x00005555556781ee in Functor<void>::operator() (this=0x555555a76e00 <Copter::scheduler_tasks>)
    at ../../libraries/AP_HAL/utility/functor.h:54
#6  0x00005555556dca49 in AP_Scheduler::run (this=0x555555aa8fd8 <copter+440>, time_available=2500)
    at ../../libraries/AP_Scheduler/AP_Scheduler.cpp:263
#7  0x00005555556dcec8 in AP_Scheduler::loop (this=0x555555aa8fd8 <copter+440>)
    at ../../libraries/AP_Scheduler/AP_Scheduler.cpp:392
#8  0x00005555556e2acf in AP_Vehicle::loop (this=0x555555aa8e20 <copter>)
    at ../../libraries/AP_Vehicle/AP_Vehicle.cpp:544
#9  0x0000555555827860 in HAL_SITL::run (this=0x555555ac4060 <hal_sitl_inst>, argc=9, argv=0x7fffffffd6f8,
    callbacks=0x555555aa8e20 <copter>) at ../../libraries/AP_HAL_SITL/HAL_SITL_Class.cpp:289
#10 0x00005555555c6877 in main (argc=9, argv=0x7fffffffd6f8) at ../../ArduCopter/Copter.cpp:892
````

> ````bash
> #4  0x00005555555c6cbd in Functor<void>::method_wrapper<AP_InertialSensor, &AP_InertialSensor::update> (
>     obj=0x555555aa9b08 <copter+3304>) at ../../libraries/AP_HAL/utility/functor.h:88
> #5  0x00005555556781ee in Functor<void>::operator() (this=0x555555a76e00 <Copter::scheduler_tasks>)
>     at ../../libraries/AP_HAL/utility/functor.h:54
> ````
>
> 这部分的函数调用是 ArduPilot 任务调度的一环

6. **发现 `_publish_gyro` 函数的实参对象是 `(instance, _imu._gyro_filtered[instance])`，进一步设置断点并跟踪**

````bash
AP_InertialSensor_Backend::update_gyro (this=0x555555b5cea0, instance=1 '\001') at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:781
781     {
(gdb) n
782         WITH_SEMAPHORE(_sem);
(gdb)
784         if (has_been_killed(instance)) {
(gdb)
787         if (_imu._new_gyro_data[instance]) {
(gdb)
788             _publish_gyro(instance, _imu._gyro_filtered[instance]);
(gdb) print &_imu._gyro_filtered
$5 = (Vector3f (*)[3]) 0x555555aaa00c <copter+4588>
(gdb) watch -location _imu._gyro_filtered[0]
Hardware watchpoint 8: -location _imu._gyro_filtered[0]
````

7. **发现是函数内部变量`gyro_filtered`直接赋值的，但该函数的传参也有 `gyro`，继续查看函数调用栈 `bt`，最终发现最初的 gyro 数据生成函数 `AP_InertialSensor_SITL::generate_gyro`**

````bash
(gdb) c
Continuing.

Thread 1 "arducopter" hit Hardware watchpoint 8: -location _imu._gyro_filtered[0]

Old value = {x = 0.00284614833, y = 0.00289227511, z = 0.00272097229}
New value = {x = 0.00284241745, y = 0.00290256576, z = 0.00272097229}
0x000055555596c0ac in AP_InertialSensor_Backend::apply_gyro_filters (this=0x555555b5cd00, instance=0 '\000', gyro=...) at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:260
260             _imu._gyro_filtered[instance] = gyro_filtered;
(gdb) bt
#0  AP_InertialSensor_Backend::apply_gyro_filters (this=0x555555b5cea0, instance=1 '\001', gyro=...)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:212
#1  0x000055555596c639 in AP_InertialSensor_Backend::_notify_new_gyro_raw_sample (this=0x555555b5cea0,
    instance=1 '\001', gyro=..., sample_us=1914234)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp:348
#2  0x00005555558efe12 in AP_InertialSensor_SITL::generate_gyro (this=0x555555b5cea0)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_SITL.cpp:302
#3  0x00005555558f0037 in AP_InertialSensor_SITL::timer_update (this=0x555555b5cea0)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor_SITL.cpp:344
#4  0x00005555558f0e19 in Functor<void>::method_wrapper<AP_InertialSensor_SITL, &AP_InertialSensor_SITL::timer_update>
    (obj=0x555555b5cea0) at ../../libraries/AP_HAL/utility/functor.h:88
#5  0x00005555556781ee in Functor<void>::operator() (this=0x555555ac4350 <HALSITL::Scheduler::_timer_proc+80>)
    at ../../libraries/AP_HAL/utility/functor.h:54
#6  0x00005555558302bc in HALSITL::Scheduler::_run_timer_procs () at ../../libraries/AP_HAL_SITL/Scheduler.cpp:253
#7  0x0000555555829ab2 in HALSITL::Scheduler::timer_event () at ../../libraries/AP_HAL_SITL/Scheduler.h:46
#8  0x000055555582a071 in HALSITL::SITL_State::_fdm_input_step (this=0x555555ac27e0 <sitlState>)
    at ../../libraries/AP_HAL_SITL/SITL_State.cpp:146
#9  0x000055555582a147 in HALSITL::SITL_State::wait_clock (this=0x555555ac27e0 <sitlState>, wait_time_usec=1914401)
    at ../../libraries/AP_HAL_SITL/SITL_State.cpp:161
#10 0x000055555582fec0 in HALSITL::Scheduler::delay_microseconds (this=0x555555ac2ce0 <sitlScheduler>, usec=1000)
    at ../../libraries/AP_HAL_SITL/Scheduler.cpp:142
#11 0x000055555582ff0c in HALSITL::Scheduler::delay (this=0x555555ac2ce0 <sitlScheduler>, ms=5)
    at ../../libraries/AP_HAL_SITL/Scheduler.cpp:151
#12 0x000055555565af13 in AP_InertialSensor::_init_gyro (this=0x555555aa9b08 <copter+3304>)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor.cpp:1726
#13 0x000055555565a176 in AP_InertialSensor::init_gyro (this=0x555555aa9b08 <copter+3304>)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor.cpp:1414
#14 0x0000555555659633 in AP_InertialSensor::init (this=0x555555aa9b08 <copter+3304>, loop_rate=400)
    at ../../libraries/AP_InertialSensor/AP_InertialSensor.cpp:959
--Type <RET> for more, q to quit, c to continue without paging--
#15 0x00005555555f9762 in Copter::startup_INS_ground (this=0x555555aa8e20 <copter>) at ../../ArduCopter/system.cpp:220
#16 0x00005555555f95a7 in Copter::init_ardupilot (this=0x555555aa8e20 <copter>) at ../../ArduCopter/system.cpp:178
#17 0x00005555556e2852 in AP_Vehicle::setup (this=0x555555aa8e20 <copter>)
    at ../../libraries/AP_Vehicle/AP_Vehicle.cpp:421
#18 0x00005555558276a4 in HAL_SITL::run (this=0x555555ac4060 <hal_sitl_inst>, argc=9, argv=0x7fffffffd618,
    callbacks=0x555555aa8e20 <copter>) at ../../libraries/AP_HAL_SITL/HAL_SITL_Class.cpp:250
#19 0x00005555555c6877 in main (argc=9, argv=0x7fffffffd618) at ../../ArduCopter/Copter.cpp:892
````

## Reference

https://ardupilot.org/dev/docs/debugging-with-gdb-on-linux.html