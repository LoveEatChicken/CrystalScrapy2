package botkit

import (
	"errors"
	"fmt"
	"io/ioutil"
	"net"
	"os"
	"runtime/debug"
	"time"

	bot "gorpcimp/bot"

	"golang.org/x/net/context"
	"google.golang.org/grpc"

	log "commonlib/beegologs"
	"commonlib/getwe/config"
)

// 中控Bot需要实现的接口
type BotStrategy interface {
	// 策略全局一次性初始化
	Init(conf config.Conf) error

	// 策略业务高并发运行
	Run(*bot.BotRequest) (*bot.BotResponse, error)
}

// Bot服务
type BotServer struct {
	bindAddr string

	conf config.Conf

	botSty BotStrategy
}

func NewBotServer() *BotServer {
	s := new(BotServer)
	s.botSty = nil
	return s
}

// 注册业务策略实现
func (s *BotServer) RegisterBotStrategy(sty BotStrategy) {
	s.botSty = sty
}

// 执行一次全局初始化
func (s *BotServer) Init(confFile string) error {

	err := s.initConf(confFile)
	if err != nil {
		return err
	}

	err = s.initLog()
	if err != nil {
		return err
	}

	err = s.botSty.Init(s.conf)
	if err != nil {
		return err
	}

	log.Llog.Info("server init finish")
	return nil
}

func (s *BotServer) initLog() error {

	local_log_channel := s.conf.StringDefault("log.locallog.max_channel_size", "100")
	llog_name := s.conf.String("log.locallog.filename")
	llog_level := s.conf.StringDefault("log.locallog.level", "6")

	log.InitFileLogger(local_log_channel, llog_name, llog_level)
	return nil
}

func (s *BotServer) initConf(confFile string) (err error) {
	s.conf, err = config.NewConf(confFile)
	if err != nil {
		return err
	}

	s.bindAddr = s.conf.String("server.bindAddr")

	return nil
}

// 多协程并发
func (s *BotServer) Work(ctx context.Context, request *bot.BotRequest) (response *bot.BotResponse, err error) {

	defer func() {
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

			log.Llog.Critical("coredump save in file : core_%s", fileName)
			response = nil
			err = errors.New("coredump")

		}
	}()

	response, err = s.botSty.Run(request)
	if err != nil {
		log.Llog.Warn("LogId[%s] Run fail : %s",
			request.LogId, err.Error())
		return nil, errors.New("bot sty run fail")
	}

	return response, nil
}

func (s *BotServer) Run() {
	lis, err := net.Listen("tcp", s.bindAddr)
	if err != nil {
		log.Llog.Critical(err.Error())
		os.Exit(1)
	}
	// server opts
	/*
		opts := make([]grpc.BotServerOption, 0, 0)
		opts = append(opts, grpc.MaxMsgSize(1024*1024*4)) // 4MB
	*/

	gs := grpc.NewServer()
	bot.RegisterBotServerServer(gs, s)
	log.Llog.Info("server running listen at : %s", s.bindAddr)
	gs.Serve(lis)

	log.Llog.Critical("server run error")
	os.Exit(1)
}
