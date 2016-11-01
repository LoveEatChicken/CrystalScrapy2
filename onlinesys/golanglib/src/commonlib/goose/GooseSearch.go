package goose

import (
	log "commonlib/beegologs"
	"commonlib/getwe/config"
	. "commonlib/goose/database"
	. "commonlib/goose/utils"
	"errors"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"runtime"
	"sync"
	"time"

	"golang.org/x/net/context"
	"google.golang.org/grpc"

	se "gorpcimp/search"
)

// Goose检索程序.核心工作是提供检索服务,同时支持动态插入索引.
type GooseSearch struct {
	conf config.Conf

	// 支持检索的db,同时提供动态插入索引功能
	searchDB *DBSearcher

	// 动态索引生成器
	varIndexer *VarIndexer

	// 检索流程
	searcher *Searcher
}

func (this *GooseSearch) Run() error {

	// read conf
	log.Llog.Debug("GooseSearch Run begin")

	bindAddr := this.conf.String("GooseSearch.Search.BindAddr")

	refreshSleepTime := this.conf.Int64("GooseSearch.Refresh.SleepTime")

	log.Llog.Debug("Read Conf bindAddr[%s] refreshSleepTime[%d]",
		bindAddr, refreshSleepTime)

	err := this.runSearchUpdateServer(bindAddr)
	if err != nil {
		return err
	}

	err = this.runRefreshServer(int(refreshSleepTime))
	if err != nil {
		return err
	}

	neverReturn := sync.WaitGroup{}
	neverReturn.Add(1)
	neverReturn.Wait()

	return nil
}

func (this *GooseSearch) Search(ctx context.Context, request *se.SeRequest) (response *se.SeResponse, err error) {
	context := NewStyContext()
	//defer context.Log.PrintAllInfo()

	t1 := time.Now().UnixNano()
	response, err = this.searcher.Search(context, request)
	t2 := time.Now().UnixNano()
	if err != nil {
		log.Llog.Warn("search fail : %s", err.Error())
		response = nil
		return
	}
	log.Llog.Info("time(ms):%d", Ns2Ms(t2-t1))

	return response, nil
}

/*
func (this *GooseSearch) SearchHandle(w http.ResponseWriter, req *http.Request) {
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

			os.Exit(1)
		}
	}()

	if req.Method != "POST" {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	context := NewStyContext()
	//defer context.Log.PrintAllInfo()

	reqbuf, err := ioutil.ReadAll(req.Body)
	if err != nil {
		log.Llog.Warn(err.Error())
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	//t1 := time.Now().UnixNano()
	resbuf, err := this.searcher.Search(context, reqbuf)
	//t2 := time.Now().UnixNano()
	if err != nil {
		log.Llog.Warn("search fail : %s", err.Error())
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
	//context.Log.Info("time(ms)", Ns2Ms(t2-t1))
	//context.Log.Info("reslen", len(resbuf))

	_, err = w.Write(resbuf)
	if err != nil {
		log.Llog.Warn("send data error : %s", err.Error())
		return
	}
}
*/

func (this *GooseSearch) UpdateHandle(w http.ResponseWriter, req *http.Request) {
	if req.Method != "POST" {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	//context := NewStyContext()
	//defer context.Log.PrintAllInfo()

	reqbuf, err := ioutil.ReadAll(req.Body)
	if err != nil {
		log.Llog.Warn(err.Error())
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
	//context.Log.Info("reqlen", len(reqbuf))

	//t1 := time.Now().UnixNano()
	err = this.varIndexer.BuildIndex(NewStringIterOnce(string(reqbuf)))
	//t2 := time.Now().UnixNano()
	if err != nil {
		log.Llog.Warn("build index fail : %s", err.Error())
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}
	//context.Log.Info("time(ms)", Ns2Ms(t2-t1))

	_, err = w.Write([]byte("{\"ret\":\"ok\"}"))
	if err != nil {
		log.Llog.Warn("send data error : %s", err.Error())
		return
	}
}

func (this *GooseSearch) runSearchUpdateServer(bindAddr string) error {

	lis, err := net.Listen("tcp", bindAddr)
	if err != nil {
		return err
	}
	// server opts
	/*
		opts := make([]grpc.ServerOption, 0, 0)
		opts = append(opts, grpc.MaxMsgSize(1024*1024*4)) // 4MB
	*/

	gs := grpc.NewServer()
	se.RegisterSearcherServer(gs, this)

	log.Llog.Info("server running listen at : %s", bindAddr)
	gs.Serve(lis)

	return nil
}

func (this *GooseSearch) runRefreshServer(sleeptime int) error {

	if 0 == sleeptime {
		log.Llog.Error(fmt.Sprintf("arg error sleeptime[%d]", sleeptime))
		return errors.New("arg error")
	}

	go func() {
		for {
			time.Sleep(time.Duration(sleeptime) * time.Second)
			log.Llog.Debug("refresh now")

			// sync search db
			err := this.searchDB.Sync()
			if err != nil {
				log.Llog.Warn(err.Error())
			}
		}
	}()

	return nil
}

func (this *GooseSearch) Init(confPath string,
	indexSty IndexStrategy, searchSty SearchStrategy) (err error) {

	// load conf
	this.conf, err = config.NewConf(confPath)
	if err != nil {
		return
	}

	// init log
	channelSize := this.conf.StringDefault("locallog.max_channel_size", "100")
	filename := this.conf.StringDefault("locallog.filename", "./log/goose.log")
	level := this.conf.StringDefault("locallog.level", "6")
	log.InitFileLogger(channelSize, filename, level)

	// set max procs
	maxProcs := int(this.conf.Int64("GooseSearch.MaxProcs"))
	if maxProcs <= 0 {
		maxProcs = runtime.NumCPU()
	}
	runtime.GOMAXPROCS(maxProcs)
	log.Llog.Debug("set max procs [%d]", maxProcs)

	// init dbsearcher
	dbPath := this.conf.String("GooseBuild.DataBase.DbPath")
	log.Llog.Debug("init db [%s]", dbPath)

	this.searchDB = NewDBSearcher()
	err = this.searchDB.Init(dbPath)
	if err != nil {
		return
	}
	log.Llog.Debug("init db [%s]", dbPath)

	// index strategy global init
	if indexSty != nil {
		err = indexSty.Init(this.conf)
		if err != nil {
			return
		}
	}
	log.Llog.Debug("index strategy init finish")

	// search strategy global init
	if searchSty != nil {
		err = searchSty.Init(this.conf)
		if err != nil {
			return
		}
	}
	log.Llog.Debug("search strategy init finish")

	// var indexer
	if indexSty != nil {
		this.varIndexer, err = NewVarIndexer(this.searchDB, indexSty)
		if err != nil {
			return
		}
	}
	log.Llog.Debug("VarIndexer init finish")

	// searcher
	if searchSty != nil {
		this.searcher, err = NewSearcher(this.searchDB, searchSty)
		if err != nil {
			return
		}
	}
	log.Llog.Debug("Searcher init finish")

	return
}

func NewGooseSearch() *GooseSearch {
	s := GooseSearch{}
	s.searchDB = nil
	s.searcher = nil
	s.varIndexer = nil
	return &s
}
