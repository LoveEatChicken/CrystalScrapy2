package main

import (
	"fmt"
	"os"

	flags "github.com/jessevdk/go-flags"

	"commonlib/getwe/utils"
)

func main() {

	defer utils.CoreDump()

	var opts struct {
		Configure string `short:"c" long:"conf" description:"congfigure file" default:"conf/qu.toml"`
	}

	parser := flags.NewParser(&opts, flags.HelpFlag)
	_, err := parser.ParseArgs(os.Args)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	svr := NewServer()
	err = svr.Init(opts.Configure)
	if err != nil {
		fmt.Println(err)
		os.Exit(2)
	}
	svr.Run()
}
