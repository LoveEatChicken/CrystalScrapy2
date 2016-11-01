package main

import (
	"fmt"
	"os"

	u "commonlib/getwe/utils"
	flags "github.com/jessevdk/go-flags"

	"commonlib/botkit"
)

func main() {

	defer u.CoreDumpExit()

	var opts struct {
		Configure string `short:"c" long:"conf" description:"congfigure file" default:"conf/qabot.toml"`
	}

	parser := flags.NewParser(&opts, flags.HelpFlag)
	_, err := parser.ParseArgs(os.Args)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	svr := botkit.NewBotServer()
	svr.RegisterBotStrategy(new(BotStrategy))
	err = svr.Init(opts.Configure)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	svr.Run()
}
