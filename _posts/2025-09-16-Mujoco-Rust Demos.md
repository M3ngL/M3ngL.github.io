---
layout: post
title: MuJoCo-Rust Demos
category: "Other"
date: 2025-09-16
---


完整代码见 https://github.com/M3ngL/mujoco-rust-demos

## Init settings

https://github.com/MuJoCo-Rust/MuJoCo-Rust 该项目是针对 MuJoCo Rust 的FFI binding

* 顶层封装使用 `mujoco-rust-0.0.6`
* 底层 binding 展示 `mujoco-rs-sys-0.0.4` https://docs.rs/mujoco-sys/latest/mujoco_sys/

该项目仅支持到 MuJoCo 2.3.5，因此需要将本地系统的 MuJoCo 设置为对应的旧版本，新版本的 MuJoCo 3.x 无法适配

MuJoCo release下载地址 https://github.com/google-deepmind/mujoco/releases/tag/2.3.5

---

MuJoCo 常用的类

* mjData
* mjContact
* mjModel
* ...

在 mujoco-rust 内主要分为了两类，`no-render, render`类，对应于非渲染和渲染类相关

使用 mujoco-rust 项目方式

````rust
use std::ptr;
let model = mujoco_rust::Model::from_xml("simple.xml".to_string()).unwrap();
let simulation = MuJoCoSimulation::new(model);
let mj_data = &*simulation.state.ptr();
let mj_contact = &*mj_data.contact;
````

---

---

Demos 主要针对无人机模型的操作以及获取相关数据，渲染画面做了解释

> 使用的无人机模型原始文件下载 https://github.com/google-deepmind/mujoco_menagerie/tree/main/skydio_x2

* **Sensor Data**，是从 mujoco-rust 加载的模型中获取传感器数据，以及根据模型名称获得其ID
* **UI**，是渲染 MuJoCo 内部画面并显示，或者合并多个画面后显示
* **Vedio Streaming**，是将渲染的画面以视频流的方式传递到其他客户端
* **Lidar**，是以多个 Rangefinder 的值绘画激光雷达图
* **Model Crash**，是获取模型碰撞的相关信息，包括碰撞点位置、碰撞数量等等

## Sensor Data

MuJoCo 能支持的sensors https://mujoco.readthedocs.io/en/stable/XMLreference.html

### How to get sensor data

1. **通过传感器定义顺序获得**

在已知模型文件中的传感器定义顺序时，可以通过访问传感器组的存储地址`sensor_adr`以及每个传感器输出数据的维度`sensor_dim`，以此为基础从传感器数据数组`sensordata()`中获取对应的传感器值

如下所示的xml文件定义sensor标签

````xml
<sensor>
    <gyro name="body_gyro" site="imu"/>
    <accelerometer name="body_linacc" site="imu"/>
    <framequat name="body_quat" objtype="site" objname="imu"/>
</sensor>
````

我们可以通过以下方式获取每种传感器对应的值，其中`sensordata()`返回的是一个数组，存储了当前时刻所有传感器的值

````rust
let model = mujoco_rust::Model::from_xml("../x2/scene.xml".to_string()).unwrap();
let mj_model = unsafe { *model.ptr() };
// 0: gyro
let gyro_start = unsafe { *mj_model.sensor_adr.add(0) } as usize;
let gyro_dim = unsafe { *mj_model.sensor_dim.add(0) } as usize;
let gyro_data = &simulation.sensordata()[gyro_start..gyro_start + gyro_dim];

// 1: accelerometer
let acc_start = unsafe { *mj_model.sensor_adr.add(1) } as usize;
let acc_dim = unsafe { *mj_model.sensor_dim.add(1) } as usize;
let acc_data = &simulation.sensordata()[acc_start..acc_start + acc_dim];

// 2: framequat
let att_start = unsafe { *mj_model.sensor_adr.add(2) } as usize;
let att_dim = unsafe { *mj_model.sensor_dim.add(2) } as usize;
let att_data = &simulation.sensordata()[att_start..att_start + att_dim];
````

2. **通过传感器名称获得**

同样需要知道模型文件中关于传感器名称的定义，如下

````xml
<body>
  <site name="rf_0" pos="0.1 0 0.05" zaxis="1 0 0"/>
  <site name="rf_15" pos="0.1 0 0.05" zaxis="0.9659 0.2588 0"/>
  <site name="rf_30" pos="0.1 0 0.05" zaxis="0.8660 0.5 0"/>
  ...
  <site name="rf_330" pos="0.1 0 0.05" zaxis="0.8660 -0.5 0"/>
  <site name="rf_345" pos="0.1 0 0.05" zaxis="0.9659 -0.2588 0"/>
</body>
...
<sensor>
  <rangefinder name="body_rf_0" site="rf_0" cutoff="10" noise="0.01"/>
  <rangefinder name="body_rf_15" site="rf_15" cutoff="10" noise="0.01"/>
  <rangefinder name="body_rf_30" site="rf_30" cutoff="10" noise="0.01"/>
  ...
  <rangefinder name="body_rf_315" site="rf_315" cutoff="10" noise="0.01"/>
  <rangefinder name="body_rf_330" site="rf_330" cutoff="10" noise="0.01"/>
  <rangefinder name="body_rf_345" site="rf_345" cutoff="10" noise="0.01"/> 
</sensor>
````

已知body标签下的`site name`，通过传入其`site name`到`name_to_id()`，返回其传感器在传感器组中的ID

再通过ID进一步从传感器值数组中获取对应的值

````rust
let model = mujoco_rust::Model::from_xml("../x2/scene.xml".to_string()).unwrap();
let mj_model = unsafe { *model.ptr() };

// get Rangefinder ids
let mut rf_ids: Vec<u16>  = Vec::new();
for angle in angles.iter() {
    let sensor_name = format!("rf_{}", angle);
    let id = model.name_to_id(ObjType::SITE, &sensor_name).unwrap();
    rf_ids.push(id);
}
// get data from id
for id in rf_ids.iter() {
    let data = simulation.sensordata()[*id as usize + 1];
    print!("rf_{}: {:?} ", id, data);
}
````

### How to get model names

之前讲到关于模型和传感器的名称，均是通过直接查验xml文件得知，但也可以通过代码获取模型文件中定义的所有结构名称，包括传感器、几何体名称、环境名称等等

````rust
use std::ffi::CStr;
use std::slice;

// get all model names
let model = mujoco_rust::Model::from_xml("../x2/scene.xml".to_string()).unwrap();
let mj_model = unsafe { *model.ptr() };
let mut model_names: Vec<&str> = Vec::new();
unsafe{
    let data = slice::from_raw_parts(mj_model.names as *const u8,
         mj_model.nnames as usize);
    let mut start = 0;
    for (i, &c) in data.iter().enumerate() {
        if c == 0 {
            let s = CStr::from_bytes_with_nul_unchecked(&data[start..=i]);
            model_names.push(s.to_str().unwrap());
            start = i + 1;
        }
    }
}
println!("{:?}", model_names);
````

## UI

https://mujoco.readthedocs.io/en/stable/programming/visualization.html

### Render scene & display

使用glfw来初始化UI窗口，并将该窗口与对应OpenGL渲染进行绑定

1. 初始化 GLFW

````rust
use glfw;
let mut glfw = glfw::init(glfw::FAIL_ON_ERRORS).unwrap();
````

2. 初始化window以及相关监听函数

````rust
use glfw;
use gl;
use glfw::Context;

// create window
let (mut window, events) = glfw
    .create_window(1200, 900, "MuJoCo UI", glfw::WindowMode::Windowed)
    .expect("Unable to create GLFW window.");

// associate GLFW window with an OpenGL state
window.make_current();

// Enable GLFW window listening for specific user input events.
window.set_key_polling(true); // keyboard input 
window.set_cursor_pos_polling(true); // mouse position
window.set_mouse_button_polling(true); // which key is pressed by the mouse 
window.set_scroll_polling(true); // mouse wheel infor

// dynamically loading OpenGL functions
gl::load_with(|symbol| window.get_proc_address(symbol) as *const _);
````

3. 进一步地，初始化mujoco render相关变量，分别是相机`cam`、场景`scn`、上下文`con`和选项`opt`

````rust
use mujoco_rs_sys::render;
use mujoco_rs_sys::no_render;

let mut cam = render::mjvCamera_::default();
let mut scn = render::mjvScene_::default();
let mut con = render::mjrContext_::default();
let mut opt = render::mjvOption_::default();

unsafe {
    no_render::mjv_defaultCamera(&mut cam);
    render::mjv_defaultScene(&mut scn);
    render::mjr_defaultContext(&mut con);

    no_render::mjv_makeScene(simulation.model.ptr(), &mut scn, 1000);
    render::mjr_makeContext(simulation.model.ptr(), &mut con, 200);
    no_render::mjv_defaultOption(&mut opt);
}
````

其中`cam`定义渲染视角，`scn`定义场景结构体，`con`封装 OpenGL 相关的状态（如着色器、纹理），`opt` 决定如何渲染场景（例如显示哪些几何体、是否启用灯光等）

至此，渲染结构体均初始化完成

4. 在主循环内实时更新每个时刻的场景

````rust
use mujoco_rs_sys::render;
use mujoco_rs_sys::no_render;


// sim running until the window closes
while !window.should_close() {
    
    // associate GLFW window with an OpenGL state
    window.make_current();

    // get window size
    let (width, height) = window.get_framebuffer_size();

    // clear buffer
    gl::Clear(gl::COLOR_BUFFER_BIT | gl::DEPTH_BUFFER_BIT);

    // update render
    no_render::mjv_updateScene(
        simulation.model.ptr(),
        simulation.state.ptr(),
        opt,
        ptr::null(),
        &mut cam,
        0xFFFFFF,
        &mut scn,
    );

    // define viewport
    let viewport = render::mjrRect_ {
        left: 0,
        bottom: 0,
        width: width,
        height: height,
    };

    // start render
    render::mjr_render(viewport, &mut scn, &mut con);

    // swap buffer to display render scene
    window.swap_buffers();
    
   	... // sim operation
    
    // Get events in real time
    glfw.poll_events();

}
````

### 1st\3rd-person perspective

指定渲染的视角为第一人称或是第三人称，要在`cam`属性中做修改

````rust
use mujoco_rs_sys::render;

let mut cam = render::mjvCamera_::default();

// No actual camera specified
cam.type_ = 1; // free perspective
cam.trackbodyid = 1; // Set tracked object ID
cam.distance = 5.0; // Set distance between perspective and model 

// actual camera specified
cam.type_ = 2; // fixed perspective
cam.fixedcamid = cam_id; // Set fixed camera id
````

mujoco render中，当没有指定实际的`camera`时，默认视角为第三人称视角，因此仅需要设置视角类型、视角跟踪移动的模型ID以及视角与模型之间的距离即可

![image-20250914162457000](/pic/image-20250914162457000.png)

当需要模仿相机实际在模型中某个位置时，需要指定camera ID，将渲染的视角设置为该camera的视角，如图所示，是以第一人称视角俯视正下方的视角

![image-20250914163021089](/pic/image-20250914163021089.png)

### Multiple perspectives in one window

将多个camera的画面渲染到一个glfw窗口中， 效果如图所示

![image-20250914162904677](/pic/image-20250914162904677.png)

由于需要管理多个视角，这里定义一个结构体方便管理，结构体中使用`Vec`存储各个camera的信息

````rust
pub struct UIState {
    pub cameras: Vec<render::mjvCamera_>,
    pub opt: render::mjvOption_,
    pub scenes: Vec<render::mjvScene_>,
    pub contexts: Vec<render::mjrContext_>,
    pub window: glfw::Window,
    pub events: mpsc::Receiver<(f64, glfw::WindowEvent)>,
}
````

首先，初始化GLFW作为全局的图形化管理框架

````rust
let mut glfw = glfw::init(glfw::FAIL_ON_ERRORS).unwrap();
````

根据不同的camera，声明各自的视角、场景以及OpenGL状态（`opt`不需要重复声明定义）

````rust
pub fn ui_init(glfw: &mut glfw::Glfw, simulation: &Simulation, cam_ids: &[i32]) -> UIState {

	... // init window & events

    // initialize MuJoCo render structure
    let mut cameras = Vec::new();
    let mut scenes = Vec::new();
    let mut contexts = Vec::new();
    let mut opt = render::mjvOption_::default();

    //Initialize scene and context for each camera
    for &cam_id in cam_ids {
        let mut cam = render::mjvCamera_::default();
        let mut scn = render::mjvScene_::default();
        let mut con = render::mjrContext_::default();
        unsafe {
            no_render::mjv_defaultCamera(&mut cam);
            render::mjv_defaultScene(&mut scn);
            render::mjr_defaultContext(&mut con);

            no_render::mjv_makeScene(simulation.model.ptr(), &mut scn, 1000);
            render::mjr_makeContext(simulation.model.ptr(), &mut con, 200);
        }
		// 1st-person perspective 
        cam.type_ = 2; // fixed perspective 
        cam.fixedcamid = cam_id;
        
        // output
        cameras.push(cam);
        scenes.push(scn);
        contexts.push(con);
    }

    unsafe {
        no_render::mjv_defaultOption(&mut opt);
    }

    UIState {
        cameras,
        opt,
        scenes,
        contexts,
        window,
        events
    }
}
````

在main函数中使用该函数的方式，传入模型文件中定义的camera ID即可

````rust
// get camera ID by specifying name
let cam1_id = simulation.model.name_to_id(ObjType::CAMERA, "camera1").unwrap() as i32;
let cam2_id = simulation.model.name_to_id(ObjType::CAMERA, "camera2").unwrap() as i32;
let cam3_id = simulation.model.name_to_id(ObjType::CAMERA, "camera3").unwrap() as i32;
let cam4_id = simulation.model.name_to_id(ObjType::CAMERA, "camera4").unwrap() as i32;

// 1st-person perspective 
let mut ui_state_1st = ui::ui_init(&mut glfw, &simulation, [cam1_id, cam2_id, cam3_id, cam4_id].as_ref());
````

同理，实时更新每个camera的渲染视角，需要将各个camera渲染的视角，各自作为主窗口的一部分导入渲染，由此其`viewport`需要重新调整定义方式

````rust
// get window size
let (width, height) = ui_state.window.get_framebuffer_size();
let num_cameras = ui_state.cameras.len().min(4);
let cols = if num_cameras < 2 { 1 } else { 2 };
let rows = if num_cameras <= 2 { 1 } else { 2 };
let sub_window_width = width / cols as i32;
let sub_window_height = height / rows as i32;

...

for i in 0..num_cameras {
    ...
    
    // calc sub window's pos in the main window
    let row = i / cols;
    let col = i % cols;

    // define sub window viewport
    let viewport = render::mjrRect_ {
        left: col as i32 * sub_window_width,
        bottom: (rows - 1 - row) as i32 * sub_window_height,
        width: sub_window_width,
        height: sub_window_height,
    };
    ...
}
````

在主循环中调用该函数，传入`init_ui()`的返回值`UI_State`即可

````rust
// 1st-person perspective 
let mut ui_state_1st = ui::ui_init(&mut glfw, &simulation, [cam1_id, cam2_id, cam3_id, cam4_id].as_ref());

// sim running until the window closes
while !ui_state_1st.window.should_close() {

    ui::update_scene(&simulation, &mut ui_state_1st);

	... // sim operation

    // Get events in real time
    glfw.poll_events();
}
````

note：同时渲染多个视角，会导致CPU负载增大许多，因此需要按需渲染

### Free glfw resource

对应的，在主循环结束后，应当释放相关资源，如下

````rust
use mujoco_rs_sys::render;

... 
unsafe{
    render::mjv_freeScene(&mut scn);
    render::mjr_freeContext(&mut con);
}
````

若是多视角的话，则在for循环中逐个释放即可

````rust
unsafe{
    for i in 0..ui_state.scenes.len() {
        render::mjv_freeScene(&mut ui_state.scenes[i]);
        render::mjr_freeContext(&mut ui_state.contexts[i]);
    }
}
````

## Vedio Streaming

1. 初始化GLFW窗口，属性设置为不可见

````rust
let mut glfw = glfw::init(glfw::FAIL_ON_ERRORS).unwrap();

let (mut window, _events) = {
    glfw.window_hint(glfw::WindowHint::Visible(false));
    glfw.create_window(640, 480, "hidden", glfw::WindowMode::Windowed)
        .expect("Unable to create hidden GLFW window.")
};
````

注意窗口的尺寸大小`640x480`应与后续的ffmpeg初始化视频流分辨率`-video_size`参数一致，否则会导致视频流画面失真

2. 初始化ffmpeg

利用`std::process::Command`调用本地系统的FFmpeg命令，并传入其命令参数

````rust
use std::process::{Command, Stdio};

let rtsp_url = "rtsp://localhost:8554/mystream".to_string();
let ffmpeg = Command::new("ffmpeg")
    .args([
        "-f", "rawvideo",
        "-pixel_format", "rgb24",
        "-video_size", "640x480",
        "-framerate", "30",
        "-i", "pipe:",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-f", "rtsp",
        "-rtsp_transport", "tcp",
        &rtsp_url
    ])
    .stdin(Stdio::piped())
    .stderr(Stdio::piped())
    .spawn() // Spawn the process
    .expect("Failed to start FFmpeg");
````

其中将该子进程的`stdin`连接到父进程（即目前的rust项目）的`stdout`，即渲染的画面帧，使得父进程能够向其写入画面帧数据

3. 逐帧渲染并传入管道

原理是在 Rust 程序中生成视频帧，然后通过 `child.stdin.unwrap().write_all(frame_bytes)` 写入管道。FFmpeg 接收管道输出，并实时编码、推送 RTSP 流，其他客户端可通过 `rtsp://localhost:8554/mystream` 播放

````rust
unsafe {
    // get window size
    let (width, height) = ui_state.window.get_framebuffer_size();

    // clear buffer
    gl::Clear(gl::COLOR_BUFFER_BIT | gl::DEPTH_BUFFER_BIT);

    // update & render
    no_render::mjv_updateScene(
        simulation.model.ptr(),
        simulation.state.ptr(),
        &ui_state.opt,
        ptr::null(),
        &mut ui_state.cam,
        0xFFFFFF,
        &mut ui_state.scn,
    );
    ... 
   	// read the main window's Pixels
    render::mjr_readPixels(rgb.as_mut_ptr(), ptr::null_mut(), full_viewport, &mut ui_state.con);
	
    // flips the image
    let mut flipped_rgb = vec![0u8; (width * height * 3) as usize];
    for y in 0..height {
        for x in 0..width {
            let src_idx = ((y * width + x) * 3) as usize;
            let dst_idx = (((height - 1 - y) * width + x) * 3) as usize;
            flipped_rgb[dst_idx] = rgb[src_idx];
            flipped_rgb[dst_idx + 1] = rgb[src_idx + 1];
            flipped_rgb[dst_idx + 2] = rgb[src_idx + 2];
        }
    }
	
    let _ = stdin.write_all(&flipped_rgb);
}
````

其中渲染画面的部分与UI渲染一致，只是在画面渲染更新后，不再调用`window.swap_buffers()`交换buffer数据以显示渲染的画面，而是读取该画面的rgb数据并返回（视频流有时会上下颠倒画面，因此还有垂直翻转rgb数据），写入管道输出

视频流效果如图（使用地面站QGC显示），FFmpeg的推送需要有类似于`mediamtx`这样的RTSP协议服务器做中介，才能传递到其他客户端显示

![image-20250916102200116](/pic/image-20250916102200116.png)

## Lidar

这部分主要解释怎么通过Mujoco model中的`rangefinder`展示出雷达图像，具体雷达图绘制算法不再赘述

概括来说，雷达图在 mujoco sim 中是使用多个`rangefinder`来实现的，`rangefinder`的传感器值为其距离可碰撞物体的距离

1. 获取rangefinder IDs

首先xml文件中定义的 `rangefinder` 格式如下

````xml
<site name="rf_0" pos="0.1 0 0.05" zaxis="1 0 0"/>
<site name="rf_15" pos="0.1 0 0.05" zaxis="0.9659 0.2588 0"/>
<site name="rf_30" pos="0.1 0 0.05" zaxis="0.8660 0.5 0"/>
<site name="rf_45" pos="0.1 0 0.05" zaxis="0.7071 0.7071 0"/>
<site name="rf_60" pos="0.1 0 0.05" zaxis="0.5 0.8660 0"/>
...
<site name="rf_300" pos="0.1 0 0.05" zaxis="0.5 -0.8660 0"/>
<site name="rf_315" pos="0.1 0 0.05" zaxis="0.7071 -0.7071 0"/>
<site name="rf_330" pos="0.1 0 0.05" zaxis="0.8660 -0.5 0"/>
<site name="rf_345" pos="0.1 0 0.05" zaxis="0.9659 -0.2588 0"/>
````

使用Sensor Data部分的方法获取ID

````rust
let mut rf_ids: Vec<u16>  = Vec::new();
let angles = [
    0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165,
    180, 195, 210, 225, 240, 255, 270, 285, 300, 315, 330, 345,
];
for angle in angles.iter() {
    let sensor_name = format!("rf_{}", angle);
    let id = model.name_to_id(ObjType::SITE, &sensor_name).unwrap();
    rf_ids.push(id);
}
````

2. 获取rangefinder的值

将每个`rangefinder`的传感器名称（以角度命名）从度转换为弧度，以表示该传感器在极坐标系中的角度；并限制`rangefinder`检测的最远距离，且筛去负值（当其值为负数时，表示无效测量，例如无障碍物）

````rust
use std::f64::consts::PI;

let mut points = Vec::new();
let angles = [
    0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165,
    180, 195, 210, 225, 240, 255, 270, 285, 300, 315, 330, 345,
];
for (i, &id) in rf_ids.iter().enumerate() {
    let distance = simulation.sensordata()[(id +1) as usize];
    let theta = angles[i] as f64 * PI / 180.0;
    if distance >= 0.0 && distance <= 10.0 {
        points.push((theta, distance));
    }
}
````

3. 绘制Lidar图

根据每个`rangefinder`的值`distance`以及其在极坐标的位置绘制，使用`minifb::window`而不是`glfw::window`，因为前者在绘制2d图像时更方便快速，代码不再赘述，效果如图所示

![image-20250916115854337](/pic/image-20250916115854337.png)

## Model Crash

与模型碰撞相关的数据有`mjData_`中的`ncon`描述当前时刻有几个碰撞点，`mjData_`的`contact`结构体中定义碰撞的相关细节

> mujoco-rust中定义的`mjData_`同`mjData`

在mujoco-rust，获取当前模型的`mjData_`方式如下

````rust
let model = mujoco_rust::Model::from_xml("../x2/scene.xml".to_string()).unwrap();
let simulation = mujoco_rust::Simulation::new(model.clone());
unsafe {
    let mj_data = &*simulation.state.ptr(); // &mjData_
}
````

进一步获取相关碰撞数据，如每个碰撞点的位置

````rust
// get contact data in mj_data
unsafe {
    let mj_data = &*simulation.state.ptr(); // mj_data needs to be updated in real time
    let ncon = mj_data.ncon as usize;
    for i in 0..ncon {
        let contact = &*mj_data.contact.add(i);
        let pos = contact.pos;
        println!(
            "contact {} at [{}, {}, {}]",
            i, pos[0], pos[1], pos[2]
        );
    }
}
````

另外，注意模型定义文件中的类别要一致，否则不计入碰撞数组，相关字段为 `contype="x" conaffinity="x"`
