package main

import (
	"net"
	"os"
	"path/filepath"
	"strings"

	qu "gorpcimp/qu"
	pm "qu/patternmatch"

	"golang.org/x/net/context"
	"google.golang.org/grpc"

	log "commonlib/beegologs"
	"commonlib/getwe/config"
)

type Server struct {
	bindAddr string

	conf config.Conf

	patDict map[string]*pm.PatternDict
}

func NewServer() *Server {
	s := new(Server)
	s.patDict = make(map[string]*pm.PatternDict)
	return s
}

func (s *Server) Init(confFile string) error {

	err := s.initConf(confFile)
	if err != nil {
		return err
	}

	err = s.initLog()
	if err != nil {
		return err
	}

	err = s.initDict()
	if err != nil {
		log.Llog.Critical("initDict fail : %s", err.Error())
		return err
	}

	log.Llog.Info("server init finish")
	return nil
}

func (s *Server) initLog() error {

	local_log_channel := s.conf.StringDefault("log.locallog.max_channel_size", "100")
	llog_name := s.conf.StringDefault("log.locallog.filename", "./log/qu.log")
	llog_level := s.conf.StringDefault("log.locallog.level", "6")

	log.InitFileLogger(local_log_channel, llog_name, llog_level)
	return nil
}

func (s *Server) initConf(confFile string) (err error) {
	s.conf, err = config.NewConf(confFile)
	if err != nil {
		return err
	}

	s.bindAddr = s.conf.StringDefault("server.bindAddr", ":7707")
	return nil
}

func (s *Server) initDict() error {
	dictPath := "./dict"
	dictPath, err := filepath.Abs(dictPath)
	if err != nil {
		log.Llog.Critical("get dict path fail : %s", err.Error())
		return err
	}

	err = filepath.Walk(dictPath, func(path string, info os.FileInfo, err error) error {
		if info == nil {
			return nil
		}
		if !info.IsDir() {
			return nil
		}
		if err != nil {
			return err
		}

		if !strings.HasSuffix(info.Name(), "_patdict") {
			return nil
		}

		dictName := strings.TrimSuffix(info.Name(), "_patdict")
		log.Llog.Debug("dict dir [%s],dict name [%s]", info.Name(), dictName)

		patternFile := filepath.Join(path, "pattern.txt")
		wordFile := filepath.Join(path, "word.txt")
		ignoreFile := filepath.Join(path, "ignore.txt")

		dict := pm.NewPatternDict()
		err = dict.Build(patternFile, wordFile, ignoreFile)
		if err != nil {
			return err
		}

		log.Llog.Info("load patdict : [%s] succ", dictName)
		s.patDict[dictName] = dict

		return nil
	})
	if err != nil {
		return err
	}
	return nil
}

// 多协程并发
func (s *Server) Parse(ctx context.Context, request *qu.QuServerRequest) (*qu.QuServerResponse, error) {
	response := new(qu.QuServerResponse)
	log.Llog.Info("logid[%s] Parse running,domain size[%d]", request.LogId,
		len(request.Domain))
	response.QuRes = make([]*qu.QuResult, 0)
	for _, domain := range request.Domain {
		dict, ok := s.patDict[domain]
		if !ok {
			log.Llog.Warn("logid[%s] domain[%s] not found", request.LogId, domain)
			continue
		}

		quRes := new(qu.QuResult)
		quRes.Domain = domain
		quRes.Intent = make([]*qu.Intent, 0)

		patRes := dict.Match(request.Query)

		log.Llog.Info("logid[%s] domain[%s] quResultCont[%d]",
			request.LogId, domain, len(patRes.Itemlist))

		for resI, item := range patRes.Itemlist {
			intent := new(qu.Intent)
			intent.ExtraAttr = item.PatternAttr
			intent.Score = 1 // TODO 目前没有打分机制
			intent.Slot = make([]*qu.Slot, 0)

			log.Llog.Info("logid[%s] domain[%s] quReIndex[%d] ExtraAttr[%s]",
				request.LogId, domain, resI, item.PatternAttr)

			for _, slot := range item.SlotList {
				idlslot := new(qu.Slot)
				idlslot.Name = slot.Name
				idlslot.Value = slot.Value

				intent.Slot = append(intent.Slot, idlslot)
			}

			quRes.Intent = append(quRes.Intent, intent)
		}

		response.QuRes = append(response.QuRes, quRes)
	}
	response.Status = 0
	return response, nil
}

func (s *Server) Run() {
	lis, err := net.Listen("tcp", s.bindAddr)
	if err != nil {
		log.Llog.Critical(err.Error())
		return
	}
	// server opts
	/*
		opts := make([]grpc.ServerOption, 0, 0)
		opts = append(opts, grpc.MaxMsgSize(1024*1024*4)) // 4MB
	*/

	gs := grpc.NewServer()
	qu.RegisterQuServerServer(gs, s)
	log.Llog.Info("server running listen at : %s", s.bindAddr)
	gs.Serve(lis)
}
