package main

import (
	"flag"
	"fmt"
	pb "gorpcimp/bot"
	"log"
	"os"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Printf("Usage:%s -addr=xxxx:xx\n", os.Args[0])
		return
	}
	paddr := flag.String("addr", "127.0.0.1:10031", "Input server address like {IP}:{PORT}.")
	flag.Parse()

	conn, err := grpc.Dial(*paddr, grpc.WithInsecure())
	if err != nil {
		log.Fatalf("did not connect: %v", err)
	}
	defer conn.Close()
	c := pb.NewBotServerClient(conn)

	// Contact the server and print out its response.
	r, err := c.Work(context.Background(), &pb.BotRequest{BotName: "chat_service",
		LogId:       "logid0001",
		UserId:      "usertest0001",
		RequestType: pb.RequestType_CONFIRM,
		Query:       "今天天气怎么样",
		UserInfo:    &pb.UserInfo{Gender: 1}})
	if err != nil {
		log.Fatalf("could not greet: %v", err)
	}
	log.Printf("Status: %d", int32(r.Status))
	if r.Status == pb.ReturnCode_SUCCESS {
		log.Printf("Content = [%s]", r.ResItem[0].Card)
	}
}
