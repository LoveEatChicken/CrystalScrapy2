package main

import (
	"flag"
	"fmt"
	"os"
	"runtime"
	"time"
)

//定义server全局变量
var Psvr *RCSvr

//主入口
func main() {
	runtime.GOMAXPROCS(runtime.NumCPU())
	if len(os.Args) < 2 {
		fmt.Printf("Usage:%s -conf=xxxx\n", os.Args[0])
		return
	}
	pconf := flag.String("conf", "./datasvr.conf", "Input config file path.")
	flag.Parse()

	fmt.Println("Current config file is :", *pconf)

	//给服务句柄赋值
	Psvr = &RCSvr{confFile: *pconf}

	//初始化服务器
	err := Psvr.Init()
	if err != nil {
		fmt.Printf("RCSvr Init(%s) failed, what = %s\n", *pconf, err)
		return
	}
	fmt.Printf("RCSvr Init(%s) success.\n", *pconf)
	Psvr.Llog.Info("Init success, pid = %d ---------------", os.Getpid())

	//注册业务处理函数
	Psvr.Register("/ai/hello", helloHandler)
	Psvr.Register("/ai/query", queryHandler)
	Psvr.Register("/ai/whiteboard", whiteBoardHandler)

	//启动服务器
	Psvr.Run()

	time.Sleep(600 * time.Second)
	return
}
