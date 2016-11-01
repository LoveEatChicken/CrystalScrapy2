package main

import (
	"fmt"
	flags "github.com/jessevdk/go-flags"
	"os"

	log "commonlib/beegologs"
	qu "gorpcimp/qu"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
)

func main() {

	var opts struct {
		Addr   string   `short:"a" long:"addr" description:"server addr" default:"127.0.0.1:10036"`
		Query  string   `short:"q" long:"query" description:"query"`
		Domain []string `short:"d" long:"domain" description:"query domain"`
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

	if len(opts.Domain) == 0 {
		parser.WriteHelp(os.Stdout)
		log.Llog.Critical("no domain input")
		os.Exit(1)
	}

	conn, err := grpc.Dial(opts.Addr, grpc.WithInsecure())
	defer conn.Close()
	if err != nil {
		log.Llog.Critical(err.Error())
		return
	}

	quClient := qu.NewQuServerClient(conn)

	request := new(qu.QuServerRequest)
	request.Query = opts.Query
	request.LogId = "123456"
	request.Domain = make([]string, len(opts.Domain))
	copy(request.Domain, opts.Domain)
	response, err := quClient.Parse(context.Background(), request)
	if err != nil {
		log.Llog.Critical(err.Error())
		return
	}
	for _, quRes := range response.QuRes {
		log.Llog.Info("domain : %s", quRes.Domain)
		for _, intent := range quRes.Intent {
			log.Llog.Info("intent : %s", intent.ExtraAttr)
			for _, slot := range intent.Slot {
				log.Llog.Info("slot\tname:%s\tvalue:%s", slot.Name, slot.Value)
			}
		}
	}
}
