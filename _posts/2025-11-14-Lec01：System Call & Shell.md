---
layout: post
title: Lec01：System Call & Shell
category: "MIT6.S081 Note"
date: 2025-11-14
---


> 课程翻译：https://mit-public-courses-cn-translatio.gitbook.io/mit6-s081/lec01-introduction-and-examples
>
> xv6教学文档：https://th0ar.gitbooks.io/xv6-chinese/content/index.html

## OS 整体设计

**操作系统的目标**

* 抽象硬件
* 多个应用程序共用硬件资源，即multiplex
* 应用程序之间相互隔离，当某个程序出现故障时不能影响其他程序
* 各个应用程序之间需要数据交互
* 操作系统用户的共享与隐私性
* 向应用程序提供高性能支持
* 操作系统需要支持不同的应用场景，如服务器或PC

**操作系统结构**

用户空间 \ 内核空间

内核空间Kernel内的服务

* 硬件资源管理
* 管理文件系统和进程管理系统
* 内存的分配
* Access Control

应用程序与Kernel的交互通过**系统调用**实现

系统调用 `open, write, fork` 简单例子如下，ta们将实际运行在系统内核中，并执行内核中对应的代码实现

````c
int fd = open("out", 1);
write(fd, "hello\n", 6);
int pid = fork()
````

## System Call是如何使用的

1. 使用 **`open` 系统调用**创建文件描述符

````c
# open.c 仅是演示代码，不是open系统调用的实现
#include "kernel/types.h"
#include "user/user.h"
#include "kernel/fcntl.h"

int main(){
    int fd = open("output", O_WRONLY | O_CREATE);
    write(fd, "ooo\n", 4);
    exit(0);
}
````

`open` 系统调用会返回一个新分配的文件描述符，是一个递增的数字

2. 使用 **`read \ write \ exit` 系统调用**实现复制 console 输入，粘贴到 console 输出 

`read` 系统调用，接收3个参数：文件描述符、指向某段内存的指针、读取的最大长度

````c
# copy.c
#include "kernel/types.h"
#include "user/user.h"

int main(){
    char buf[64];
    while(1){
        int n = read(0, buf, sizeof(buf));
        if(n <= 0) break;
        write(1, buf, n);
    }
    exit(0);
}
````

其中文件描述符`0`，在 shell 程序中指代 console 的输入，文件描述符 `1` 指代console 的输出

优化copy程序的思路：捕获系统调用可能的报错，即返回值，并处理

3. 使用 **`fork` 系统调用** 创建新进程

````c
# fork.c 仅是演示代码，不是fork系统调用的实现
#include "kernel/types.h"
#include "user/user.h"

int main(){
    int pid = fork();
    
  	if(pid == 0){
        printf("child\n");
    }else{
        printf("parent\n");
    }
    
    exit(0);
}
````

`fork` 会拷贝当前进程的内存，并创建一个新的进程，这里的内存包含了进程的指令和数据

> 父子进程在 xv6 的实现中完全相同，包括文件描述符表单的拷贝

* 在原始的进程中，fork系统调用会返回大于0的整数，即是新创建进程的ID。
* 在新创建的进程中，fork系统调用会返回0。

执行该程序 `fork.c` 将导致父子进程同时运行，使得 console 输出时看到两个进程混淆在一起的字符输出

在 Shell 中运行程序，实际上 Shell 会创建一个新的进程来运行输入的每一个指令，新的进程运行指令也需要进行系统调用 `exec`

4. 使用 **`exec \ wait` 系统调用**执行其他指令并接收子进程运行状态

````c
# exec.c 仅是演示代码，不是exec系统调用的实现

#include "kernel/types.h"
#include "user/user.h"

int main(){
    char *argv[] = {"echo", "this", "is", "echo", 0};
    exec("echo", argv);
    printf("exec failed!\n");
    exit(1);
}
````

执行 `exec` 系统调用将丢弃当前进程的内存，转而加载的目标文件中的指令并执行。在这一过程中能够传入命令行参数数组 `char *argv[]`

* `exec` 系统调用会保留当前的文件描述符表单
* `exec` 系统调用正常执行不会返回，因为内存被完全替换，相当于当前进程不复存在了，所以 `exec` 系统调用已经没有地方能返回了
* `exec` 系统调用只会当出错时才会返回，比如某些错误会阻止操作系统运行文件中的指令

因此 `exec.c` 后半段的 `printf, exit` 在程序正常执行过程中不会被执行到

Shell 会将 `fork` 和 `exec` 连起来使用，如

````c
# forkexec.c

int main(){
    int pid, status, child;
    pid = fork();
    
    if(pid == 0){
        char *argv[] = {"echo", "this", "is", "echo", 0};
        exec("exec", argv);
        printf("exec failed!\n");
        exit(1);
    }else{
        printf("parent waiting.");
        child = wait(&status);
        printf("child %d exited with status: %d\n", child, status);
    }
    exit(0);
}

````

子进程（`pid=0`）会用 `echo` 命令来代替自己，`echo` 执行完成之后就退出，将操作系统控制权还给父进程

父进程部分，执行的 `wait` 系统调用，接收参数 `&status`，是一种让退出的子进程以一个整数格式与等待的父进程通信方式，即将 `status` 对应的地址传递给内核，内核会向这个地址写入子进程向 `exit` 传入的参数；`wait` 系统调用返回接收到退出的子进程的PID号

一般来说，`exit` 的参数选择是固定的

* 如果一个程序成功的退出了，那么 `exit` 的参数会是0
* 如果出现了错误，会向 `exit` 传递1

> 如果子进程调用了 `wait`，由于子进程自己没有子进程了，所以 `wait` 会立即返回 `-1`，表明出现错误：当前的进程并没有任何子进程。

优化思路：默认的 `fork` 系统调用会拷贝当前进程的所有内存，但实际情况中并不需要这么多的资源，因此可以进一步优化，仅拷贝执行 `exec` 所需要的内存

> 在编译之后，C程序就是一些在内存中的指令，这些指令存在于内存中；所以这些指令可以被拷贝，因为它们就是内存中的字节，它们可以被拷贝到别处

## Shell & Redirect

当在 Shell 中输入内容时，实际上是告诉 Shell 运行相应的程序。

比如当输入 `ls` 时，实际的意义是我要求 Shell 运行名为 `ls` 的程序，文件系统中会有一个文件名为 `ls`，这个文件中包含了一些计算机指令，最终 Shell 将运行位于文件 `ls` 内的这些计算机指令。

Shell 中重定向符号的简单使用

````bash
ls > out # 将 ls 程序返回的内容写入 out 文件
grep x < out # 将 out 文件的内容导入 grep 程序中
````

程序实现重定向

````c
# redirect.c 仅是演示代码，不是重定向符号的实现

int main(){
    int pid;
    
    pid = fork();
    if(pid == 0){
        close(1);
        open("output", O_WRONLY | O_CREATE);
        
        char *argv[] =  {"echo", "this", "is", "redirect", "echo", 0};
        exec("echo", argv);
        printf("exec failed\n");
    }else{
        wait((int *) 0);
    }
    exit(0);
}
````

运行该程序将导致 `echo` 本来输出到 console 的字符，输入到了 `output` 文件中

这是因为子进程中的 `close(1)` 改变了 Shell 程序中默认的文件描述符，具体来说，程序手动关闭了文件描述符`1`；又调用 `open` 打开了一个新的文件描述符，而 `open` 会返回当前进程未使用的最小文件描述符序号，这里即是 `1`

> 文件描述符 `0` 由于没有被 `close`，因此依旧代表 console 的输入
>
> 子进程中调用 `close`，不会影响到父进程的文件描述符

因此此时子进程中的文件描述符 `1` 不再指代 console 的输出，而是指代对 `output` 文件的写入

而 `echo` 指令默认会输出到文件描述符 `1`，进而输入到了 `output` 文件中，就此完成了重定向

> `echo` 指令始终将输出指向文件描述符 `1`，不管文件描述符 `1`是指代的什么
