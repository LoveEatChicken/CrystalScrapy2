package main

import (
	"flag"
	"fmt"
	pb "gorpcimp/bot"
	"os"
	"time"

	"google.golang.org/grpc"
)

//定义server全局变量
var Psvr *ChatSvr

//主入口
func main() {
	if len(os.Args) < 2 {
		fmt.Printf("Usage:%s -conf=xxxx\n", os.Args[0])
		return
	}
	pconf := flag.String("conf", "./charsvr.toml", "Input config file path.")
	flag.Parse()

	fmt.Println("Current config file is :", *pconf)

	//初始化服务器
	Psvr = &ChatSvr{confFile: *pconf}
	err := Psvr.Init()
	if err != nil {
		fmt.Printf("ChatSvr Init(%s) failed, what = %s\n", *pconf, err)
		return
	}
	fmt.Printf("ChatSvr Init(%s) success.\n", *pconf)
	Psvr.Llog.Info("Init success, pid = %d ---------------", os.Getpid())

	//启动grpc服务
	s := grpc.NewServer()
	pb.RegisterBotServerServer(s, Psvr)
	s.Serve(*Psvr.ListenHandle())

	time.Sleep(600 * time.Second)
	return
}
