package main

import (
	"fmt"
	flags "github.com/jessevdk/go-flags"
	"os"

	log "commonlib/beegologs"
	se "gorpcimp/search"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
)

func main() {

	var opts struct {
		Addr  string `short:"a" long:"addr" description:"server addr" default:"10.10.139.235:10035"`
		Query string `short:"q" long:"query" description:"query"`
	}

	parser := flags.NewParser(&opts, flags.HelpFlag)
	_, err := parser.ParseArgs(os.Args)
	if err != nil {
		fmt.Println(err.Error())
		os.Exit(1)
	}

	if len(opts.Query) == 0 {
		parser.WriteHelp(os.Stdout)
		log.Llog.Critical("no query input")
		os.Exit(1)
	}

	conn, err := grpc.Dial(opts.Addr, grpc.WithInsecure())
	defer conn.Close()
	if err != nil {
		log.Llog.Critical(err.Error())
		return
	}

	seClient := se.NewSearcherClient(conn)

	request := new(se.SeRequest)
	request.Query = opts.Query
	request.IsDebug = true
	request.PageNum = 0
	request.PageSize = 5
	request.LogId = "123456"

	response, err := seClient.Search(context.Background(), request)
	if err != nil {
		log.Llog.Critical(err.Error())
		return
	}

	for _, seRes := range response.ResList {
		log.Llog.Info("bweight[%d] weight[%d]", seRes.Bweight, seRes.Weight)
		log.Llog.Info("debug info :")
		fmt.Println(seRes.Debug)
		log.Llog.Info("data info :")
		fmt.Println(seRes.Data)
	}
}
