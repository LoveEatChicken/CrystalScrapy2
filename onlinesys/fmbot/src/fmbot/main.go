package main

import (
	"fmt"
	"os"

	u "commonlib/getwe/utils"
	flags "github.com/jessevdk/go-flags"

	"commonlib/botkit"
)

func main() {

	defer u.CoreDump()

	var opts struct {
		Configure string `short:"c" long:"conf" description:"congfigure file" default:"conf/fmbot.toml"`
	}

	parser := flags.NewParser(&opts, flags.HelpFlag)
	_, err := parser.ParseArgs(os.Args)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	svr := botkit.NewBotServer()
	// 提供一个实例注册进入
	svr.RegisterBotStrategy(new(BotStrategy))
	err = svr.Init(opts.Configure)
	if err != nil {
		fmt.Println(err)
		os.Exit(2)
	}
	svr.Run()
}
