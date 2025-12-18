---
layout: post
title: xv6-Lab1：Utilities
category: "MIT6.S081 Note"
date: 2025-11-15
---


> 课程作业：https://pdos.csail.mit.edu/6.828/2022/labs/util.html
>
> 第三方答案：
>
> * https://github.com/relaxcn/xv6-labs-2022-solutions/blob/main/doc/utils.md
> * https://blog.miigon.net/posts/s081-lab1-unix-utilities/

如何编写满足要求的代码，参考课程答案中都有，这里主要展开看看用到的xv6系统调用函数的定义实现等

## sleep 

> Implement the UNIX program `sleep` for xv6; your `sleep` should pause for a user-specified number of ticks. A tick is a notion of time defined by the xv6 kernel, namely the time between two interrupts from the timer chip. Your solution should be in the file `user/sleep.c`.

````c
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int main(int argc, char* argv[]){
    if(argc != 2){
        printf("Usage: sleep [time].");
        exit(1);
    }
    int time = atoi(argv[1]);
    if(sleep(time) != 0){
        printf("Sleep: Wrong with sleep.");
        exit(1);
    }
    exit(0);
}
````

直接调用实现好的 `sleep` 系统调用，以及字符串转数值的现成函数 `atoi`

1. 展开看一看xv6如何从调用用户空间的函数，到内核空间的系统调用函数的，以`sleep`系统调用为例

在用户空间查询 `sleep()` 函数的定义，只能跳转到 `user/user.h` 中对 `sleep()` 的声明

````c
struct stat;

// system calls
...
int sleep(int);
...
````

关键的跳转点位于 `user/usys.S`

````nasm
.global sleep
sleep:
 li a7, SYS_sleep
 ecall
 ret
````

项目编译后，用户空间调用 `sleep` 函数会找到这里，并执行其中的指令

* `a7` 是软件层面指代的寄存器
* `SYS_sleep` 定义在 `kernel/syscall.c`，实际是指针数组 `syscalls` 的索引，用于定位内核空间实现的函数指针 `sys_sleep`
* `ecall` 是 RISC-V 指令集的**自陷指令**

`ecall` 指令执行时会让系统根据 **a7** 寄存器的值来确定系统调用的类型（这里就是刚刚赋值给 `a7` 的 `SYS_sleep`），并执行对应的系统调用，直接结束后返回（即 `ret`），继续执行用户程序

> 具体的，`ecall` 指令如何到内核空间中，并执行相关函数使得内核空间的`sys_sleep`函数得到执行，之后章节会有讨论，这里暂不深究

后续`sys_sleep`函数内部的逻辑简单来说，外层`while`循环判断仿真硬件时钟与初始记录时间的差值是否超过用户设置的时间

````c
ticks0 = ticks;
while(ticks - ticks0 < n){ ... }
````

若差值暂时还没有超过 `n` 则继续执行循环内的内容，如下

````c
sleep(&ticks, &tickslock);
````

该函数内部将全局变量 `ticks` 的地址赋值给该进程的字段 `chan`，表示该进程正在等待 `ticks` 变量变化（即等待时钟中断）

````c
// Go to sleep.
p->chan = chan;
p->state = SLEEPING;
````

并调用`sched()`函数，进一步调用调度器让cpu处理其他需要进行的进程

`ticks` 变量本身在时钟中断时自增，并调用 `wakeup` 函数唤醒进程

````c
void clockintr()
{
  acquire(&tickslock);
  ticks++;
  wakeup(&ticks);
  release(&tickslock);
}
````

> 软件时钟中断的调用逻辑： `kernel/trap.c -> kerneltrap() -> devintr() -> clockintr()`

`wakeup(&ticks)` 会将等待 `ticks` 变量变化的进程字段`state`设置为`RUNNABLE`

````c
void wakeup(void *chan){
  struct proc *p;

  for(p = proc; p < &proc[NPROC]; p++) {
    if(p != myproc()){
      acquire(&p->lock);
      if(p->state == SLEEPING && p->chan == chan) {
        p->state = RUNNABLE;
      }
      release(&p->lock);
    }
  }
}
````

调度器重新发现该进程处于 `RUNNABLE`，便让cpu处理该进程

2. 展开看看简易版的 `atoi`函数的实现（不能跳过空格等无关字符）

````c
int
atoi(const char *s)
{
  int n;

  n = 0;
  while('0' <= *s && *s <= '9')
    n = n*10 + *s++ - '0';
  return n;
}

````

以输入 `"123"` 为例，`n` 初始化为 `0`，看 while 内部循环逻辑

1. 第一个字符 `'1' - '0'` 等于数值 `1`；数值 `0*10 + 1 = 1` 赋值给 `n`
2. 继续循环，`1*10 + '2' - '0' = 12`赋值给 `n`，以此类推，得到数值 `123`

## pingpong 

> Write a program that uses UNIX system calls to ''ping-pong'' a byte between two processes over a pair of pipes, one for each direction. The parent should send a byte to the child; the child should print "<pid>: received ping", where <pid> is its process ID, write the byte on the pipe to the parent, and exit; the parent should read the byte from the child, print "<pid>: received pong", and exit. Your solution should be in the file `user/pingpong.c`.

````c
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

int main(){
    int pingpong[2];
    if(pipe(pingpong) < 0){
        printf("pingpong: pipe failed\n");
        exit(1);
    }
    // printf("%d, %d", pingpong[0], pingpong[1]);

    int pid = fork();
    if(pid == 0){
        int child = getpid();
        char msg[4];
        if(read(pingpong[0], msg, sizeof(msg)) != -1){
            printf("%d: received %s\n", child, msg);
            strcpy(msg, "pong");
            write(pingpong[1], msg, sizeof(msg));
            exit(0);
        }
    }else{
        int parent = getpid();
        char msg[4] = "ping";
        write(pingpong[1], msg, sizeof(msg));
        if(read(pingpong[0], msg, sizeof(msg)) != -1){
            printf("%d: received %s\n", parent, msg);
        }
    }
    exit(0);
}
````

初次使用管道 `pipe`，看看背后的实现，如何实现一个通道专门用作读，另一个通道专门用作写

> 下一题 primes 在展开看看 `read, write` 系统调用如何实现的

```` c
uint64
sys_pipe(void)
{
  uint64 fdarray; // user pointer to array of two integers
  struct file *rf, *wf;
  int fd0, fd1;
  struct proc *p = myproc();

  argaddr(0, &fdarray);
  if(pipealloc(&rf, &wf) < 0)
    return -1;
  fd0 = -1;
  if((fd0 = fdalloc(rf)) < 0 || (fd1 = fdalloc(wf)) < 0){
    if(fd0 >= 0)
      p->ofile[fd0] = 0;
    fileclose(rf);
    fileclose(wf);
    return -1;
  }
  if(copyout(p->pagetable, fdarray, (char*)&fd0, sizeof(fd0)) < 0 ||
     copyout(p->pagetable, fdarray+sizeof(fd0), (char *)&fd1, sizeof(fd1)) < 0){
    p->ofile[fd0] = 0;
    p->ofile[fd1] = 0;
    fileclose(rf);
    fileclose(wf);
    return -1;
  }
  return 0;
}
````

关键函数 `pipealloc, fdalloc, copyout`，以及结构体 `file`，`file` 结构体定义中包含了 `pipe` 结构体

````c
struct file {
  enum { FD_NONE, FD_PIPE, FD_INODE, FD_DEVICE } type;
  int ref; // reference count
  char readable;
  char writable;
  struct pipe *pipe; // FD_PIPE
  struct inode *ip;  // FD_INODE and FD_DEVICE
  uint off;          // FD_INODE
  short major;       // FD_DEVICE
};

struct pipe {
  struct spinlock lock;
  char data[PIPESIZE];
  uint nread;     // number of bytes read
  uint nwrite;    // number of bytes written
  int readopen;   // read fd is still open
  int writeopen;  // write fd is still open
};
````

结构体 `file` 中的 `FD_PIPE, FD_INODE, FD_DEVICE` 分别代表管道，文件或目录，磁盘文件

结构体 `pipe` 中的 `nread, nwrite` 分别代表管道中的读写指针，用于判定管道中的数据是否读取完成（读写指针指向一致时读取完成）

> 虽然称作`nread, nwrite` 为读写指针，但并不是真的指针类型，仅是 `uint` 类型用作管道缓冲区的索引指针

1. 下面看 `pipealloc` 函数的定义

````c
int
pipealloc(struct file **f0, struct file **f1)
{
  struct pipe *pi;

  pi = 0;
  *f0 = *f1 = 0;
  if((*f0 = filealloc()) == 0 || (*f1 = filealloc()) == 0)
    goto bad;
  if((pi = (struct pipe*)kalloc()) == 0)
    goto bad;
  pi->readopen = 1;
  pi->writeopen = 1;
  pi->nwrite = 0;
  pi->nread = 0;
  initlock(&pi->lock, "pipe");
  (*f0)->type = FD_PIPE;
  (*f0)->readable = 1;
  (*f0)->writable = 0;
  (*f0)->pipe = pi;
  (*f1)->type = FD_PIPE;
  (*f1)->readable = 0;
  (*f1)->writable = 1;
  (*f1)->pipe = pi;
  return 0;

 bad:
    ...
  return -1;
}
````

首先调用 `filealloc()` 正式的记录 `f0,f1` 在文件系统中的索引，并返回索引赋值给 `f0,f1`

初始化一个 `pi` ，分配内存，并指定当前管道既能读也能写 `pi->readopen = 1; pi->writeopen = 1;`

将赋值完成的 `pi` 分配给两个文件 `f0,f1`，相当于这两个文件共用一个 `pi`，只是各自只有读写权限中的一个

````c
(*f0)->readable = 1;
(*f0)->writable = 0;
...
(*f1)->readable = 0;
(*f1)->writable = 1;
````

至此，`pipealloc`函数成功结束

2. `fdalloc` 函数仅是分配空置的文件描述符给 `file` 结构体对象
3. `copyout` 函数，将内核空间的信息通过页表的方式传递到用户空间，具体逻辑涉及到页表等概念，暂不讨论

##  primes 

> Write a concurrent version of prime sieve using pipes. This idea is due to Doug McIlroy, inventor of Unix pipes. The picture halfway down [this page](http://swtch.com/~rsc/thread/) and the surrounding text explain how to do it. Your solution should be in the file `user/primes.c`.

````c
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

void filter(int *pre_p){
    close(pre_p[1]);

    int prime;
    if(read(pre_p[0], &prime, sizeof(int)) != 4){ // 递归的退出条件判断
        close(pre_p[0]);
        exit(0);
    }
    printf("prime %d\n", prime);

    // 创建管道
    int p[2];
    if(pipe(p) < 0){
        printf("error: pipe create p wrong.");
        exit(1);
    }

    // 并发运行
    if(fork() == 0){
        filter(p); // 进入递归
        exit(0);
    }else{
        close(p[0]); // 将父进程的所有管道都关闭，这样才能正常退出程序
        int num;
        while(read(pre_p[0], &num, sizeof(int)) == 4){
            if(num % prime != 0){
                write(p[1], &num, sizeof(int));
            }
        }
        close(pre_p[0]);
        close(p[1]);

        wait((int*)0); // 父进程都必须wait所有的子进程
    }
}

int main(){
    int p[2];
    if(pipe(p) < 0){
        printf("error: pipe create p wrong.");
        exit(1);
    }
    for(int i = 2; i <= 35; i++){
        write(p[1], &i, sizeof(int));
    }
    filter(p);
    exit(0);
}
````

递归 + 创建管道，使得程序能够**并发**解决问题
$$
\text{filter}(S) = 
\begin{cases}
\text{return \ 0} & \text{if } \text{read}(S) = \emptyset \\
\text{write}\ \ p \quad \text{if} \ (x \mod p \not\equiv 0) & \text{otherwise}
\end{cases}
$$
`fork()` 和 `wait()` 必须一一对应，否则父进程无法退出，导致控制权回不到 Shell 程序中

展开看看 `read` 系统调用，从用户空间到内核空间的调用逻辑和 `sleep` 系统调用一致

````c
uint64 sys_read(void){
  struct file *f;
  int n;
  uint64 p;

  argaddr(1, &p);
  argint(2, &n);
  if(argfd(0, 0, &f) < 0)
    return -1;
  return fileread(f, p, n);
}
````

该函数主要是过渡，将用户空间的参数通过寄存器传递到内核空间中，进一步传递到内核空间中的 `fileread` 函数中

````c
// Read from file f.
// addr is a user virtual address.
int fileread(struct file *f, uint64 addr, int n) {
  int r = 0;

  if(f->readable == 0)
    return -1;

  if(f->type == FD_PIPE){
    r = piperead(f->pipe, addr, n);
  } else if(f->type == FD_DEVICE){
    if(f->major < 0 || f->major >= NDEV || !devsw[f->major].read)
      return -1;
    r = devsw[f->major].read(1, addr, n);
  } else if(f->type == FD_INODE){
    ilock(f->ip);
    if((r = readi(f->ip, 1, addr, f->off, n)) > 0)
      f->off += r;
    iunlock(f->ip);
  } else {
    panic("fileread");
  }

  return r;
}
````

目前用到的是 `r = piperead(f->pipe, addr, n);`，其他类型的文件读取逻辑暂不讨论

````c
int piperead(struct pipe *pi, uint64 addr, int n){
  int i;
  struct proc *pr = myproc();
  char ch;

  acquire(&pi->lock);
  while(pi->nread == pi->nwrite && pi->writeopen){  //DOC: pipe-empty
    if(killed(pr)){
      release(&pi->lock);
      return -1;
    }
    sleep(&pi->nread, &pi->lock); //DOC: piperead-sleep
  }
  for(i = 0; i < n; i++){  //DOC: piperead-copy
    if(pi->nread == pi->nwrite)
      break;
    ch = pi->data[pi->nread++ % PIPESIZE];
    if(copyout(pr->pagetable, addr + i, &ch, 1) == -1)
      break;
  }
  wakeup(&pi->nwrite);  //DOC: piperead-wakeup
  release(&pi->lock);
  return i;
}
````

按顺序拆开来看，注意其中有对管道的锁的占用和释放 `acquire(&pi->lock); ... release(&pi->lock);` ，下面主要讲实际处理逻辑

````c
  while(pi->nread == pi->nwrite && pi->writeopen){  //DOC: pipe-empty
    if(killed(pr)){
      release(&pi->lock);
      return -1;
    }
    sleep(&pi->nread, &pi->lock); //DOC: piperead-sleep
  }
````

第一段处理逻辑是当读写指针指向相同时（也就是没有新的内容可以读取了）且写端依然还开着，那么读端进程将进入睡眠状态，等待管道 `pi` 字段 `nread`  指针的变化

>  `pipewrite` 函数内部将调用 `wakeup(&pi->nread)` 来唤醒等待 `pi` 字段 `nread`  指针变化的进程，也就是读端进程
>
>  `piperead` 函数内部将调用 `wakeup(&pi->nwrite)` 来唤醒等待 `pi` 字段 `nwrite`  指针变化的进程，也就是写端进程
>
> 这样设计的机制就是 “生产者-消费者” 同步机制

````c
  for(i = 0; i < n; i++){  //DOC: piperead-copy
    if(pi->nread == pi->nwrite)
      break;
    ch = pi->data[pi->nread++ % PIPESIZE];
    if(copyout(pr->pagetable, addr + i, &ch, 1) == -1)
      break;
  }
  wakeup(&pi->nwrite);  //DOC: piperead-wakeup
  release(&pi->lock);
  return i;
````

第二段逻辑是根据用户传入的参数 `n`，即一次读取/写入的最大字符数量，在 `for` 循环中逐个读取管道中的数据 `pi->data`，并写入页表，方便系统调用结束返回用户空间后，用户空间的函数获取这些数据 `pi->data`

`write`  系统调用下的 `pipewrite` 函数逻辑和 `piperead` 互补，不再讨论

## find 

> Write a simple version of the UNIX find program: find all the files in a directory tree with a specific name. Your solution should be in the file `user/find.c`.

````c
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"
#include "kernel/fs.h"

void
find(char *path, char *pattern)
{
  char buf[512], *p;
  int fd;
  struct dirent de;
  struct stat st;

  if((fd = open(path, 0)) < 0){
    fprintf(2, "find: cannot open %s\n", path);
    return;
  }

  if(fstat(fd, &st) < 0){
    fprintf(2, "find: cannot stat %s\n", path);
    close(fd);
    return;
  }

  switch(st.type){
  case T_DEVICE:
  case T_FILE:
  case T_DIR:
    if(strlen(path) + 1 + DIRSIZ + 1 > sizeof buf){
      printf("find: path too long\n");
      break;
    }
    strcpy(buf, path);
    p = buf+strlen(buf);
    *p++ = '/';
    while(read(fd, &de, sizeof(de)) == sizeof(de)){
        if(de.inum == 0) continue;
        memmove(p, de.name, DIRSIZ);
        p[DIRSIZ] = 0;
        if(stat(buf, &st) < 0){
            printf("find: cannot stat %s\n", buf);
            continue;
        }

        if(strcmp(".", de.name) == 0 || strcmp("..", de.name) == 0) continue;
        if(st.type == T_DIR){
            if(strcmp(de.name, pattern) == 0) printf("%s/\n", buf); // 文件夹名称若符合pattern也一同返回
            find(buf, pattern);
        }else if(st.type == T_FILE){
            if(strcmp(de.name, pattern) == 0) printf("%s\n", buf);
        }
    }
    break;
  }
  close(fd);
}


int main(int argc, char* argv[]){
    if(argc != 3){
        printf("usage: find [path] pattern.\n");
    }
    find(argv[1], argv[2]);
    exit(0);
}
````

根据 `user/ls.c` 的实现修改的来，主要看看 `ls.c` 中 `ls` 用户空间指令的实现

````c
void ls(char *path){
  char buf[512], *p;
  int fd;
  struct dirent de;
  struct stat st;

  if((fd = open(path, 0)) < 0){
    fprintf(2, "ls: cannot open %s\n", path);
    return;
  }

  if(fstat(fd, &st) < 0){
    fprintf(2, "ls: cannot stat %s\n", path);
    close(fd);
    return;
  }

  switch(st.type){
  case T_DEVICE:
  case T_FILE:
    printf("%s %d %d %l\n", fmtname(path), st.type, st.ino, st.size);
    break;

  case T_DIR:
    if(strlen(path) + 1 + DIRSIZ + 1 > sizeof buf){
      printf("ls: path too long\n");
      break;
    }
    strcpy(buf, path);
    p = buf+strlen(buf);
    *p++ = '/';
    while(read(fd, &de, sizeof(de)) == sizeof(de)){
      if(de.inum == 0)
        continue;
      memmove(p, de.name, DIRSIZ);
      p[DIRSIZ] = 0;
      if(stat(buf, &st) < 0){
        printf("ls: cannot stat %s\n", buf);
        continue;
      }
      printf("%s %d %d %d\n", fmtname(buf), st.type, st.ino, st.size);
    }
    break;
  }
  close(fd);
}
````

关键结构体  `struct dirent` 和 `struct stat` 

````c
struct dirent {
  ushort inum;
  char name[DIRSIZ];
};

struct stat {
  int dev;     // File system's disk device
  uint ino;    // Inode number
  short type;  // Type of file
  short nlink; // Number of links to file
  uint64 size; // Size of file in bytes
};
````

1. 关键函数 `fstat`，调用后到内核空间的处理逻辑 `fstat -> sys_fstat -> filestat`

 ````c
 // Get metadata about file f.
 // addr is a user virtual address, pointing to a struct stat.
 int
 filestat(struct file *f, uint64 addr)
 {
   struct proc *p = myproc();
   struct stat st;
   
   if(f->type == FD_INODE || f->type == FD_DEVICE){
     ilock(f->ip);
     stati(f->ip, &st);
     iunlock(f->ip);
     if(copyout(p->pagetable, addr, (char *)&st, sizeof(st)) < 0)
       return -1;
     return 0;
   }
   return -1;
 }
 ````

判断当前的文件类型是否为文件/目录/磁盘，如果是的话则从内核空间文件系统中记录的文件**元数据**拷贝给 `st`，将 `st` 写入页表

> 元数据包括文件所在的磁盘 `dev`，文件在文件系统中的唯一标识符 `ino`，文件类型 `type`，硬链接数 `nlink`，文件大小 `size`

2. 进入 `switch` 逻辑，分为 `T_DEVICE, T_FILE, T_DIR`，主要看看 `T_DIR` 情况下的

````c
strcpy(buf, path);
p = buf+strlen(buf);
*p++ = '/';
````

先将当前的文件路径 `path` 写入 `buf`，设置指针 `p` 指向 `buf` 的最高位

通过指针 `p` 向 `buf` 写入 `/`，表示为下一层目录

````c
while(read(fd, &de, sizeof(de)) == sizeof(de)){
  if(de.inum == 0)
    continue;
  memmove(p, de.name, DIRSIZ);
  p[DIRSIZ] = 0;
  if(stat(buf, &st) < 0){
    printf("ls: cannot stat %s\n", buf);
    continue;
  }
  printf("%s %d %d %d\n", fmtname(buf), st.type, st.ino, st.size);
}
````

这里的 `read` 系统调用将进入之前没有提到的文件系统中的读取，这里也暂时不讨论，读取的内容是目录项下的各个文件名，读取赋值给 `de.name`；

之后再调用 `memmove(p, de.name, DIRSIZ)` 将 `de.name` 通过指针 `p` 写入 `buf`；紧接着 `p[DIRSIZ] = 0` 作为字符串结尾

**note：**`p` 指向的位置并没有发生改变，这意味着 `while` 循环下，同一目录下的其他文件名继续在同一个位置写入 `buf`，覆盖之前写入的文件名

主要处理逻辑看完了，其他函数比如 `fmtname` 是整理输出的字符串形式的，以空格补充文件名到文件类型之间的距离，使得输出更美观，如下面，也就是文件名到后面数字的空格

````bash
$ ls
.              1 1 1024
..             1 1 1024
README         2 2 2227
xargstest.sh   2 3 93
````

## xargs 

> Write a simple version of the UNIX xargs program: its arguments describe a command to run, it reads lines from the standard input, and it runs the command for each line, appending the line to the command's arguments. Your solution should be in the file `user/xargs.c`.

````c
#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

void run(char *path, char **argv){
    if(fork() == 0){
        exec(path, argv);
        exit(1);
    }else{
        wait((int *) 0);
    }
}

int main(int argc, char* argv[]){
    if(argc < 2){
        printf("usage: xargs command [params].\n");
    }

    char *argsbuf[128];
    char **args_ponit = argsbuf;
    // 将argv先写入new_argv
    for(int i = 1; i < argc; i++){
        *args_ponit++ = argv[i];
    }
    // 获取console的输入并整合到new_argv
    char s, buf[512];
    char *p = buf;
    while(read(0, &s, sizeof(char)) == 1){
        if(s == '\n'){
            *p++ = '\0'; // 分割字符串
            *args_ponit++ = buf;
            run(argv[1], argsbuf);
            p = buf; // 重置指针
            args_ponit--; // 重置指针
            continue;
        }
        *p++ = s; // 获取console的连贯输入作为单个字符串
    }
    *p++ = '\0';
    *args_ponit++ = buf;
    run(argv[1], argsbuf);

    while (wait(0) != -1);
    exit(0);
}
````

注意 `exec` 指令传入的参数列表，也得包括命令本身比如

````c
exec('echo', ['echo', 'hello', 'world']);
````

重点是当 console 输入中有 `\n` 时，需要单独作为一次命令执行，比如 `xargstest.sh` 内的指令

````bash
mkdir a
echo hello > a/b
mkdir c
echo hello > c/b
echo hello > b
find . b | xargs grep hello
````

执行 `find . b` 将返回

````
./a/b
./c/b
./b
````

使用管道传输的内容也就是 `./a/b\n./c/b\n./b\n`，而 `grep` 指令不可能执行 `grep hello ./a/b ./c/b ./b`，因此需要分开执行

## Reference

https://ysyx.oscc.cc/docs/ics-pa/3.2.html#x86