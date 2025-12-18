---
layout: post
title: xv6-Lab2：System Call
category: "MIT6.S081 Note"
date: 2025-12-02
---


> 课程作业：https://pdos.csail.mit.edu/6.828/2022/labs/syscall.html
>
> 第三方答案：
>
> - https://github.com/relaxcn/xv6-labs-2022-solutions/blob/main/doc/syscall.md
> - https://blog.miigon.net/posts/s081-lab2-system-calls/

**Analysis** 分析过程中的代码不一定是最后的完整实现，完整实现可以见我的仓库 [commit](https://github.com/M3ngL/xv6-labs-2022-ans/commits/syscall/)

## Using gdb

该作业是跟着官方 hint 对 xv6 进行gdb调试，并回答系统进行的某些细节，作业内容以及回答具体见第三方答案

xv6 根目录中分为两个终端运行以下命令，即可开始gdb调试

终端1

````bash
make qemu-gdb
````

终端2

````bash
riscv64-unknown-elf-gdb -x .gdbinit
````

其中 `.gdbinit` 文件内容是 gdb 预运行的命令，包括加载符号文件 `kernel/kernel`

> 加载符号文件 `symbol-file` 的作用是每个函数、变量、源码行对应的内存地址
>
> 虽然 `kernel` 是二进制可执行文件，但其中也包含了符号文件的内容，因此可以作为符号文件 `.sym` 加载

目前只加载了内核空间的符号文件，若要调试用户空间的符号文件，则需要加载对应函数所在的编译好的二进制文件，如要调试 `runcmd` 函数，则需要加载 `user/_sh` 作为符号文件

````bash
symbol-file user/_sh
````

![image-20251202093925197](/pic/image-20251202093925197.png)

## System call tracing

> In this assignment you will add a system call tracing feature that may help you when debugging later labs. You'll create a new `trace` system call that will control tracing. It should take one argument, an integer "mask", whose bits specify which system calls to trace. For example, to trace the fork system call, a program calls `trace(1 << SYS_fork)`, where `SYS_fork` is a syscall number from `kernel/syscall.h`. You have to modify the xv6 kernel to print out a line when each system call is about to return, if the system call's number is set in the mask. The line should contain the process id, the name of the system call and the return value; you don't need to print the system call arguments. The `trace` system call should enable tracing for the process that calls it and any children that it subsequently forks, but should not affect other processes.

### Analysis

> 任务的需求分析

**总体实现目标**：当在 Shell 中执行 `trace` 时，该指令会跟踪命令参数中的执行情况，如

````bash
trace 32 grep hello README
````

* `32` 为传入 `trace` 指令的参数，该参数表示本次执行 `trace` 指令，需要跟踪/打印的系统调用是哪些（不是所有系统调用都要打印）

执行效果：将  `grep hello README` 命令中涉及到的系统调用情况打印出来

````bash
3: syscall read -> 1023
3: syscall read -> 966
3: syscall read -> 70
3: syscall read -> 0
````

分别是PID号、系统调用种类以及系统调用的返回值

---

由此，分为几个部分/问题来实现

1. 由于执行的 `trace` 指令实际处理过程是在内核空间中（打印系统信息只能在内核空间中），需要实现新的系统调用 `sys_trace`
2. `trace` 指令参数由用户空间到内核空间的传递，以及参数解析
3. 确定打印的系统信息来源、打印条件以及执行打印函数的位置

---

**新的系统调用 `sys_trace` 实现**

官方已提供了 `user/trace.c`，能够在用户空间执行 `trace` 指令，并接收来自 Shell 输入的参数

````c
#include "kernel/param.h"
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int main(int argc, char *argv[]){
  int i;
  char *nargv[MAXARG];

  if(argc < 3 || (argv[1][0] < '0' || argv[1][0] > '9')){
    fprintf(2, "Usage: %s mask command\n", argv[0]);
    exit(1);
  }

  if (trace(atoi(argv[1])) < 0) {
    fprintf(2, "%s: trace failed\n", argv[0]);
    exit(1);
  }
  
  for(i = 2; i < argc && i < MAXARG; i++){
    nargv[i-2] = argv[i];
  }
  exec(nargv[0], nargv);
  exit(0);
}
````

`trace.c` 中调用了函数 `trace`，这需要我们实现从用户空间 `trace` 函数到内核空间的 `sys_trace` 函数的过程

> * `trace.c` 编译成功后，是可以在 Shell 中执行的指令
> * `trace` 函数是在代码中调用的，不是 Shell 指令
>
> 因此，之后说到的 `trace` 指令和 `trace` 函数不是一个东西

具体需要做的是：

1. 用户空间 `trace` 函数的声明以及编译目标
   * 在 `user/user.h` 中加入`trace` 函数的声明 `int trace(int mask);`
   * 在`Makefile` 中加入 `$U/_trace\`

2. 用户空间函数调用到内核空间的跳转
   * 在 `user/usys.pl` 加入汇编函数 `entry("trace");`

3. 在内核空间中加入 `sys_trace` 函数的声明
   * 在 `kernel/syscall.c` 中加入 `extern uint64 sys_trace(void);`

另外，由于是创建新的系统调用函数，需要在系统调用数组增加相应的函数指针，以及定义新的索引

在 `kernel/syscall.h` 中加入 `#define SYS_trace  22`

在 `kernel/syscall.c -> syscall_names` 数组中加入新的索引以及对应的函数指针 `[SYS_trace]   sys_trace`

---

**`trace` 指令参数传递以及解析处理**

`user/trace.c` 中已实现将来自 Shell 的参数获取，并将第一个参数转换为数值类型，传入 `trace` 函数；其余参数由 `exec` 指令另行执行

因此我们需要在 `trace` 函数跳转到内核空间后，在内核空间获取并处理该传参

根据官方 hint，需要参考 `kernel/sysproc.c` 中实现的函数例子，在内核空间获取用户空间的参数；以及`sys_trace` 函数中需要将传入的数值型参数 `mask`，写入当前进程 `proc` 的字段中，以方便打印时获取，以及父进程向子进程传递 `mask`

因此，我们需要做

* 在 `struct proc` 定义中加入新字段，以存储 `mask`

````c
// Per-process state
struct proc {
  struct spinlock lock;

  // p->lock must be held when using these:
  enum procstate state;        // Process state
  void *chan;                  // If non-zero, sleeping on chan
  int killed;                  // If non-zero, have been killed
  int xstate;                  // Exit status to be returned to parent's wait
  int pid;                     // Process ID

  // wait_lock must be held when using this:
  struct proc *parent;         // Parent process

  // these are private to the process, so p->lock need not be held.
  uint64 kstack;               // Virtual address of kernel stack
  uint64 sz;                   // Size of process memory (bytes)
  pagetable_t pagetable;       // User page table
  struct trapframe *trapframe; // data page for trampoline.S
  struct context context;      // swtch() here to run process
  struct file *ofile[NOFILE];  // Open files
  struct inode *cwd;           // Current directory
  char name[16];               // Process name (debugging)
  int trace_mask;             // Trace mask for system calls // newly added
};
````

* 在内核空间中通过访问寄存器 `a0` 的值来获取用户空间的传参

````c
int n;
argint(0, &n);
````

>  官方将获取寄存器数据的 `argint` 函数实现在了 `kernel/syscall.c`

* 将已经传递到内核空间的传参赋值给 `proc -> trace_mask`

根据 xv6 的实现习惯，`sys_trace` 函数内部并不执行实际的处理逻辑，而是仅负责参数传递；由 `sys_trace` 函数跳转到内核空间的 `trace` 函数中，进行实际的处理（将`mask` 赋值给 `proc` 结构体字段）

> 内核空间的 `trace` 函数和用户空间调用的 `trace` 函数并不是一个函数，这两个是分别编译到了两个二进制文件中，因此不冲突

````c
// kernel/sysproc.c
...
uint64
sys_trace(void){
  int n;
  argint(0, &n);
  trace(n);
  return 0;
}
...
    
// kernel/proc.c
void
trace(int mask){
  struct proc *p = myproc();
  p->trace_mask = mask;
  return;
}
````

内核空间中的 `trace` 函数也需要声明，位于 `kernel/defs.h`，增加 `void trace(int mask);`

---

**打印函数的位置、打印条件以及打印信息**

根据官方 hint，**打印位置**是选择在  `kernel/syscall.c -> syscall()` 函数中，选择在这里的意义是当所有的系统调用正常返回时，都会执行到这一步，由此实现对所有的系统调用都进行判定，判定是否需要打印本次系统调用的信息

````c
void syscall(void){
  int num;
  struct proc *p = myproc();

  num = p->trapframe->a7;
  if(num > 0 && num < NELEM(syscalls) && syscalls[num]) {
    // Use num to lookup the system call function for num, call it,
    // and store its return value in p->trapframe->a0
    p->trapframe->a0 = syscalls[num]();
  } else {
    printf("%d %s: unknown sys call %d\n",
            p->pid, p->name, num);
    p->trapframe->a0 = -1;
  }
}
````

该函数在 `if` 语句条件中通过索引 `syscalls[num]` 执行了对应的函数，即系统调用 

````c
num > 0 && num < NELEM(syscalls) && syscalls[num]
````

执行成功后，将进入 `if` 语句的真分支，将系统调用的返回值赋值给 `a0` 寄存器

我们需要在系统调用执行结束并且正常返回后，执行打印函数，因此在 **`if` 语句条件为真的逻辑中**增加打印逻辑

确定**是否打印该系统调用的条件**，需要根据 `mask` 的意义来看

根据题目信息：将整数 `mask` 作为参数，该**掩码的位**指定要跟踪的系统调用

因此，判断的条件是 `(mask >> sys_call_index) & 1`，其中 `sys_call_index` 是该系统调用在函数指针对照表中的索引

需要**打印的系统信息**是PID号、系统调用种类以及系统调用的返回值，其中系统调用种类是需要字符返回的，因此我们还需要定义一个名称映射表

在 `kernel/syscall.c` 中定义新的字符数组

````c
static char *syscall_names[] = {
    [SYS_fork]    "fork",
    [SYS_exit]    "exit",
    [SYS_wait]    "wait",
    [SYS_pipe]    "pipe",
    [SYS_read]    "read",
    [SYS_kill]    "kill",
    [SYS_exec]    "exec",
    [SYS_fstat]   "fstat",
    [SYS_chdir]   "chdir",
    [SYS_dup]     "dup",
    [SYS_getpid]  "getpid",
    [SYS_sbrk]    "sbrk",
    [SYS_sleep]   "sleep",
    [SYS_uptime]  "uptime",
    [SYS_open]    "open",
    [SYS_write]   "write",
    [SYS_mknod]   "mknod",
    [SYS_unlink]  "unlink",
    [SYS_link]    "link",
    [SYS_mkdir]   "mkdir",
    [SYS_close]   "close",
    [SYS_trace]   "trace"
};
````

其他需要打印的信息均是在 `syscall` 函数中可以直接获取到的，如PID号可以通过访问进程 `proc` 的字段 `pid` 获得， 系统调用的返回值之前已经赋值给了 `a0` 寄存器，直接获取即可

在这里的总体实现，也就是

````c
if(num > 0 && num < NELEM(syscalls) && syscalls[num]) {
    // Use num to lookup the system call function for num, call it,
    // and store its return value in p->trapframe->a0
    p->trapframe->a0 = syscalls[num]();

    int up_mask = (1 << NELEM(syscall_names)) - 1;
    if(((p->trace_mask & up_mask) >> num) & 1){
      printf("%d: syscall %s -> %d\n", p->pid, syscall_names[num], p->trapframe->a0);
    }
} 
````

其中 `up_mask` 是确保用户输入的参数不会影响到系统本身的稳定，对参数做位运算，防止超过索引数组大小的二进制位也进入处理逻辑

### Issue

* 从用户空间到内核空间的传参过程中，是什么时候将参数存储在 `a0` 寄存器中的？

RISC-V ABI规定，当实参作为形参传入函数中时，都将按顺序存入 `a0` 到 `a7` 寄存器，多余的参数就将存入栈中

由**编译器自动实现**这一过程，C语言代码不需要显式实现这一过程

在 xv6 代码中，可以直接通过 `p->trapframe->a0` 来访问到仿真的 `a0` 寄存器，这是因为进入 trap（中断/系统调用）时，xv6 编写的 trap 入口汇编代码会按固定顺序把所有通用寄存器手动保存到 trapframe 的对应偏移位置

以 `sys_sleep` 函数为例，gdb调试，断点打在了 `sys_sleep` 开头，设置 `watchpoint $a0 $a1`

C 语言代码如下

````c
uint64 sys_sleep(void){
  int n;
  uint ticks0;
  argint(0, &n);
  ...
}
````

函数开始时，`a0, a1` 寄存器的值如下

````bash
(gdb) info r a0 a1
a0             0x80008fe0       2147520480
a1             0x9      9
````

按源码顺序执行，可以发现在正式进入 `argint(0, &n);` 语句之前，`a0, a1` 寄存器的值均在汇编层面被修改

```` bash
(gdb) n
57        argint(0, &n);
(gdb) n

Thread 2 hit Watchpoint 5: $a1

Old value = 9
New value = 274877882252
0x0000000080002126 in sys_sleep () at kernel/sysproc.c:57
57        argint(0, &n);
(gdb) n

Thread 2 hit Watchpoint 4: $a0

Old value = 2147520480
New value = 0
0x0000000080002128 in sys_sleep () at kernel/sysproc.c:57
57        argint(0, &n);
````

此时执行到的位置与 `=>` 一致，前后汇编代码如下，

````nasm
   0x8000211e <sys_sleep+10>:   sd      s3,24(sp)
   0x80002120 <sys_sleep+12>:   add     s0,sp,64
   0x80002122 <sys_sleep+14>:   add     a1,s0,-52
   0x80002126 <sys_sleep+18>:   li      a0,0
=> 0x80002128 <sys_sleep+20>:   auipc   ra,0x0
   0x8000212c <sys_sleep+24>:   jalr    -450(ra)
   0x80002130 <sys_sleep+28>:   auipc   a0,0xc
````

---

* 当没有执行 `trace` 指令时，OS进行的系统调用不应该出现打印信息，为什么会没有打印信息？

因为 `proc` 结构体中的 `mask` 字段在初始化时，位于**全局区域**，这将导致所有未初始化的字段都会被置为 `0`

````c
// kernel/proc.c
struct proc proc[NPROC];
````

如果没有指令传入新的参数，那么 `syscall` 函数内部的逻辑判断不会走到 `printf` 函数部分

## Sysinfo 

> In this assignment you will add a system call, `sysinfo`, that collects information about the running system. The system call takes one argument: a pointer to a `struct sysinfo` (see `kernel/sysinfo.h`). The kernel should fill out the fields of this struct: the `freemem` field should be set to the number of bytes of free memory, and the `nproc` field should be set to the number of processes whose `state` is not `UNUSED`. We provide a test program `sysinfotest`; you pass this assignment if it prints "sysinfotest: OK".

### Analysis

**实现效果1：**官方在用户空间提供了测试程序 `user/sysinfotest.c`，我们是通过在 Shell 执行编译好的 `sysinfotest` 程序来测试是否通过

因此需要在 `Makefile` 中加入该文件作为编译链接目标

**实现效果2：**`sysinfotest.c` 中将调用 `sysinfo` 系统调用，这由我们实现：

* 从用户空间到内核空间的流程实现与 System call tracing 一致，不再赘述
* 该系统调用内部将**获取系统的剩余内存与正在使用的进程数量**，并赋值给在用户空间创建的 `struct sysinfo` 的字段

具体地，赋值过程是**从内核空间到用户空间**，根据官方 hint，参考 `filestat() (kernel/file.c)` 中的实现，使用 `copyout` 函数，根据位于用户空间的结构体的地址，来直接赋值

---

**从内核空间到用户空间的赋值**

首先要将用户空间的结构体地址传递到内核空间，与上一题一致，调用专用于获取用户空间的传参的函数

这里是获取地址，因此使用 `argaddr` 函数，而不是 `argint` 函数

````c
uint64 addr;
argaddr(0, &addr);
sysinfo(addr);
````

在内核空间中的实际处理函数 `sysinfo` 中，使用 `copyout` 函数将初始化并赋值好的结构体传到用户空间

````c
struct sysinfo sinfo;
struct proc *p = myproc();
sinfo.nproc = func1_result();
sinfo.freemem = func2_result();
copyout(p->pagetable, addr, (char *)&sinfo, sizeof(sinfo));
````

之所以能直接使用进程的页表 `p->pagetable` 来确定写入点在内存中的位置，是因为同一个进程内切换用户态和内核态，所运行的代码和使用的数据都是在一个虚拟页表中，因此数据传递可以通过在进程的页表中使用偏移量，即这里的 `addr`，就能将内核空间数据传递到用户空间

> 用户态时不能通过同一页表访问内核态，这是因为页表中高地址的内核区域只有内核态才能访问，用户态不能访问

**`sys_sysinfo` 系统调用返回值确定**

由于 `sysinfotest.c` 中有对 `sysinfo` 系统调用返回值的判断，以此来查看是否成功执行：

````c
...
if (sysinfo(&info) < 0) {
    printf("FAIL: sysinfo failed\n");
    exit(1);
}
...
if (sysinfo((struct sysinfo *) 0xeaeb0b5b00002f5e) !=  0xffffffffffffffff) {
    printf("FAIL: sysinfo succeeded with bad argument\n");
    exit(1);
}
...
````

因此我们在实现该系统调用时，要注意返回值的选用

````c
uint64 sys_sysinfo(void){
  uint64 addr;
  argaddr(0, &addr);
  if(sysinfo(addr) < 0){
    return -1;
  }else{
    return 0;
  }
}
````

当执行成功时，返回 `0`，执行失败时，返回 `-1`

返回 `-1` 是因为系统调用函数返回值为 `uint64` 类型，在机器中表示 `-1` ，将自动变成 `0xffffffffffffffff`，这将与 `sysinfotest.c` 中的第二个 `if` 语句匹配

 进一步地，要求具体处理逻辑的实现部分：位于内核空间的 `sysinfo` 函数也要注意返回值

````c
int
sysinfo(uint64 addr){
    ...
    if(copyout(p->pagetable, addr, (char *)&sinfo, sizeof(sinfo)) < 0){
        return -1;
    }else{
        return 0;
    }
}
````

---

**获取系统的剩余内存**

根据官方 hint，这部分的函数要实现在 `kernel/kalloc.c`，参考该文件的其他函数实现方式，如 `kalloc`

````c
struct run {
  struct run *next;
};
struct {
  struct spinlock lock;
  struct run *freelist;
} kmem;

void * kalloc(void){
  struct run *r;

  acquire(&kmem.lock);
  r = kmem.freelist;
  if(r)
    kmem.freelist = r->next;
  release(&kmem.lock);

  if(r)
    memset((char*)r, 5, PGSIZE); // fill with junk
  return (void*)r;
}
````

该函数实现了内核页级内存的分配（页表内部填充 `5`，防止内核使用未初始化的内存），其中的结构体 `run` 代表一页物理内存；`kmem` 代表内核的页内存管理器，该变量的结构体字段：

* `lock` 是保护 `freelist` 的自旋锁，保证多核/多线程下的安全
* `freelist` 是空闲物理页链表的头指针

综上，空闲内存页表将由链表的方式存储，如下

````
kmem.freelist -> run1 -> run2 -> run3 -> ...
````

因此，我们根据该链表结构，逐一访问每个空闲页，并累计计算的空闲页的字节数，就能获取当前系统的剩余内存

每页的大小固定为 `PGSIZE`，宏定义为 `4096`

````c
uint64 calc_free_mem(void){
  uint64  free_mem = 0;
  struct run *r;
  acquire(&kmem.lock);
  r = kmem.freelist;
  while(r){
    free_mem += PGSIZE;
    r = r->next;
  }
  release(&kmem.lock);
  return free_mem;
}
````

---

**获取系统当前运行的进程数量**

根据官方 hint，这需要实现在 `kernel/proc.c`，参考该文件中的其他函数，如 `procdump `函数

````c
#define NPROC        64  // maximum number of processes
struct proc proc[NPROC];
void procdump(void){
  static char *states[] = {
  [UNUSED]    "unused",
  [USED]      "used",
  [SLEEPING]  "sleep ",
  [RUNNABLE]  "runble",
  [RUNNING]   "run   ",
  [ZOMBIE]    "zombie"
  };
  struct proc *p;
  char *state;

  printf("\n");
  for(p = proc; p < &proc[NPROC]; p++){
    if(p->state == UNUSED)
      continue;
    if(p->state >= 0 && p->state < NELEM(states) && states[p->state])
      state = states[p->state];
    else
      state = "???";
    printf("%d %s %s", p->pid, state, p->name);
    printf("\n");
  }
}
````

该函数的作用是打印进程列表，包含进程的PID号、状态、名称

关键是也对所有进程进行了一次遍历，对每个进程进行了相关判断

````c
for(p = proc; p < &proc[NPROC]; p++){
````

其中 `proc[NPROC]` 是系统当前的所有进程信息存储的数组， `NPROC` 代表进程数量的上限，而 `p++` 等价于 `原地址 + sizeof(struct proc)`

更改一下 `procdump` 函数的 `if` 语句判断条件，就能符合我们的需求了

````c
uint64 calc_process_num(void){
  uint64 process_num = 0;
  struct proc *p;
  for(p = proc; p < &proc[NPROC]; p++) {
    if(p->state != UNUSED){
      process_num++;
    }
  }
  return process_num;
}
````

> note：实现的`calc_process_num`与`calc_free_mem`函数均要在 `kernel/defs.h` 中进行声明

至此，实现了该作业的全部内容

### Issue

* `copyout` 函数设置的形参类型为什么要是 `char *`

我们注意到在使用 `copyout` 函数时，传参过程前对 `sinfo` 进行了类型强制转换，转换为了 `char *`

这是因为 `copyout` 函数形参类型设置为了 `char *`

为什么使用的是 `char *` 而不是其他的类型？

这是因为将传入的内容看作字节流，以此来进行的页表写入，而 `char` 类型是最能反映字节流的单位

> C语言 中 `char ` 是最小的寻址单位（1 字节）

````c
int copyout(pagetable_t pagetable, uint64 dstva, char *src, uint64 len){
  uint64 n, va0, pa0;

  while(len > 0){
    va0 = PGROUNDDOWN(dstva);
    pa0 = walkaddr(pagetable, va0);
    if(pa0 == 0)
      return -1;
    n = PGSIZE - (dstva - va0);
    if(n > len)
      n = len;
    memmove((void *)(pa0 + (dstva - va0)), src, n);

    len -= n;
    src += n;
    dstva = va0 + PGSIZE;
  }
  return 0;
}
````

* 如何从代码上判断空闲页表的存储方式

````c
struct run {
  struct run *next;
};
````

该结构是**自引用结构**，在结构体定义内部有一个指针，指向另一个同样的 `run` 结构体

使用该结构体可以迅速创建**单向链表**

````c
// 创建三个节点，形成链表： A → B → C → nullptr
struct run c = { NULL };     	// 尾节点
struct run b = { &c };          // b 指向 c
struct run a = { &b };          // a 指向 b
struct run *head = &a;          // 链表头指针，指向第一个节点
````

## xv6 System Call 流程

在用户空间和内核空间之间，有一个叫做 `Syscall` 的中间层，是连接用户态和内核态的桥梁。

1. 准备阶段

   1. 用户空间中定义含有系统调用函数的用户函数。该文件需要有（引用）声明，声明系统调用函数，即`user/user.h`。也有部分用户空间的文件名与系统调用函数同名，这相当于系统调用函数的前端（因为要向系统调用函数传递来自用户的参数），如`trace`

      > `user/user.h`虽然声明了系统调用函数，但是在IDE中是无法通过该声明找到定义的，因为系统调用函数实现的文件位置在`Kernel`而不在`user`文件夹

   2. 执行pl脚本`usys.pl`通过硬编码方式生成汇编代码`usys.S`，也就是汇编存根，如下

````nasm
 trace:
     li a7, SYS_trace		
     ecall				# ecall调用system call,跳到内核态的统一系统调用处理函数syscall()
     ret
````

其中RISCV的`ecall`指令（该指令固定查看`a7`寄存器来确定syscall的类型）会跳转到内核态，

2. 编译链接阶段

   1. 用户空间定义的函数编译成对应的`function.o`，该文件中的系统调用函数目前仅是符号，暂未知道确切调用该函数的地址。`usys.S `编译成对应的 `usys.o`，该文件中有系统调用函数该执行的代码段落（并不是系统调用的实际定义），以`trace`为例，这将调用`ecall`，该指令将实际进行系统调用，从用户态切换到内核态
   2. 链接器将二者链接到一起，生成可执行文件`trace`

3. 运行阶段

   1. 用户在shell中执行用户命令（该命令包括系统调用），以`trace`为例，

   ````bash
   trace 10 ls
   ````

   2. 系统执行 `/trace` 文件，首先进入该指令的“前端”，初步处理用户的参数。再执行用户空间 `trace()` 函数（实际上是系统调用存根），这将触发系统调用 `ecall` 指令
   3. 内核处理该系统调用指令

   > `ecall` 触发陷阱，进入内核的 `usertrap` -> `syscall` 函数。
   >
   > `syscall` 函数会读取 `a7` 中的 `SYS_trace` 系统调用号。
   >
   > 它会从 `syscalls` 数组中找到 `sys_trace` 函数的地址，并调用 `sys_trace()`
   >
   > `sys_trace()` 函数会从当前进程的 `trapframe` 中获取 `a0` 寄存器中的参数值（即 10）。
   >
   > `sys_trace` 函数将这个掩码 (`10`) 存储到当前进程的 `p->trace_mask` 字段中。
   >
   > `sys_trace` 返回 0（成功），这个返回值被放入当前进程的 `trapframe->a0` 中。

   4. 内核通过 `usertrapret`返回到用户空间的 `trace` 程序的 `main` 函数
