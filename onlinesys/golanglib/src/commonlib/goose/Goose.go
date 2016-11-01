package goose

import (
	log "commonlib/beegologs"
	u "commonlib/getwe/utils"
	"fmt"
	flags "github.com/jessevdk/go-flags"
	"os"
)

// goose的入口程序.
type Goose struct {
	// 建库策略
	indexSty IndexStrategy
	// 检索策略
	searchSty SearchStrategy

	// 配置文件
	confPath string

	// 建库模式数据文件
	dataPath string
}

func (this *Goose) SetIndexStrategy(sty IndexStrategy) {
	this.indexSty = sty
}

func (this *Goose) SetSearchStrategy(sty SearchStrategy) {
	this.searchSty = sty
}

// 程序入口,解析程序参数,启动[建库|检索]模式
func (this *Goose) Run() {
	defer func() {
		if r := recover(); r != nil {
			os.Exit(1)
		}
	}()

	// 解析命令行参数
	var opts struct {
		// build mode
		BuildMode bool `short:"b" long:"build" description:"run in build mode"`

		// configure file
		Configure string `short:"c" long:"conf" description:"congfigure file" default:"conf/goose.toml"`

		// build mode data file
		DataFile string `short:"d" long:"datafile" description:"build mode data file"`
	}
	parser := flags.NewParser(&opts, flags.HelpFlag)
	_, err := parser.ParseArgs(os.Args)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	if opts.BuildMode && len(opts.DataFile) == 0 {
		parser.WriteHelp(os.Stderr)
		os.Exit(1)
	}

	this.confPath = opts.Configure
	this.dataPath = opts.DataFile

	log.Llog.Debug("Load log conf finish")

	// run
	if opts.BuildMode {
		err = this.buildModeRun()
	} else {
		err = this.searchModeRun()
	}
	if err != nil {
		os.Exit(2)
	}
}

// 建库模式运行
func (this *Goose) buildModeRun() error {

	if this.indexSty == nil {
		log.Llog.Error("Please set index strategy,see Goose.SetIndexStrategy()")
		return u.ErrFmt("no strategy")
	}

	gooseBuild := NewGooseBuild()
	err := gooseBuild.Init(this.confPath, this.indexSty, this.dataPath)
	if err != nil {
		fmt.Println(err)
		log.Llog.Error(err.Error())
		return u.ErrFmt("goose build init fail")
	}

	err = gooseBuild.Run()
	if err != nil {
		log.Llog.Error(err.Error())
		return u.ErrFmt("goose run fail")
	}

	return nil

}

// 检索模式运行
func (this *Goose) searchModeRun() error {

	log.Llog.Debug("run in search mode")

	if this.searchSty == nil {
		log.Llog.Error("Please set search strategy,see Goose.SetSearchStrategy()")
		return u.ErrFmt("no strategy")
	}

	if this.indexSty == nil {
		log.Llog.Warn("can't build index real time witout Index Strategy")
	}

	gooseSearch := NewGooseSearch()
	err := gooseSearch.Init(this.confPath, this.indexSty, this.searchSty)
	if err != nil {
		log.Llog.Error(err.Error())
		return u.ErrFmt("goose search init fail")
	}

	log.Llog.Debug("goose search init succ")

	err = gooseSearch.Run()
	if err != nil {
		log.Llog.Error(err.Error())
		return u.ErrFmt("goose run fail")
	}

	return nil
}

func NewGoose() *Goose {
	g := Goose{}
	g.indexSty = nil
	g.searchSty = nil
	return &g
}
