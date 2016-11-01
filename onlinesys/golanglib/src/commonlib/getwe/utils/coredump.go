package utils

import (
	"fmt"
	"io/ioutil"
	"os"
	"runtime/debug"
	"time"
)

// 捕获异常，模拟c程序输出coredump信息至磁盘然后退出
func CoreDumpExit() {
	if r := recover(); r != nil {
		fmt.Println(r)
		stackInfo := debug.Stack()
		fmt.Println(string(stackInfo))
		t := time.Now()
		timeStr := t.Format("20060102_150405")
		fileName := fmt.Sprintf("%s_%d", timeStr, t.Unix())

		ioutil.WriteFile(fmt.Sprintf("core_%s", fileName), stackInfo, 0644)
		f, _ := os.Create(fmt.Sprintf("heapdump_%s", fileName))
		defer f.Close()
		debug.WriteHeapDump(f.Fd())

		os.Exit(1)
	}

}

// 打印coredump不退出进程
func CoreDumpContinue() {
	if r := recover(); r != nil {
		fmt.Println(r)
		stackInfo := debug.Stack()
		fmt.Println(string(stackInfo))
		t := time.Now()
		timeStr := t.Format("20060102_150405")
		fileName := fmt.Sprintf("%s_%d", timeStr, t.Unix())

		ioutil.WriteFile(fmt.Sprintf("core_%s", fileName), stackInfo, 0644)
		f, _ := os.Create(fmt.Sprintf("heapdump_%s", fileName))
		defer f.Close()
		debug.WriteHeapDump(f.Fd())
	}
}
