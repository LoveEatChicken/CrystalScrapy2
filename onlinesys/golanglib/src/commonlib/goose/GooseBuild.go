package goose

import (
	log "commonlib/beegologs"
	"commonlib/getwe/config"
	. "commonlib/goose/database"
	. "commonlib/goose/utils"
	"os"
	"runtime"
)

// Goose的静态库生成程序.
type GooseBuild struct {
	conf config.Conf

	staticDB *DBBuilder

	staticIndexer *StaticIndexer

	fileHd   *os.File
	fileIter *FileIter
}

func (this *GooseBuild) Run() (err error) {
	defer this.fileHd.Close()

	// build index
	err = this.staticIndexer.BuildIndex(this.fileIter)
	if err != nil {
		return err
	}

	// db sync
	err = this.staticDB.Sync()
	if err != nil {
		return err
	}

	return nil
}

// 根据配置文件进行初始化.
// 需要外部指定索引策略,策略可以重新设计.
// 需要外部知道被索引文件(这个易变信息不适合放配置)
func (this *GooseBuild) Init(confPath string, indexSty IndexStrategy, toIndexFile string) (err error) {
	// load conf
	this.conf, err = config.NewConf(confPath)
	if err != nil {
		return
	}

	// init log
	local_log_channel := this.conf.StringDefault("locallog.max_channel_size", "100")
	llog_name := this.conf.StringDefault("locallog.filename", "./log/goose.log")
	llog_level := this.conf.StringDefault("locallog.level", "7")

	err = log.InitFileLogger(local_log_channel, llog_name, llog_level)

	// set max procs
	maxProcs := int(this.conf.Int64("GooseBuild.MaxProcs"))
	if maxProcs <= 0 {
		maxProcs = runtime.NumCPU()
	}
	runtime.GOMAXPROCS(maxProcs)

	// init dbbuilder
	dbPath := this.conf.String("GooseBuild.DataBase.DbPath")
	transformMaxTermCnt := this.conf.Int64("GooseBuild.DataBase.TransformMaxTermCnt")
	maxId := this.conf.Int64("GooseBuild.DataBase.MaxId")
	maxIndexFileSize := this.conf.Int64("GooseBuild.DataBase.MaxIndexFileSize")
	maxDataFileSize := this.conf.Int64("GooseBuild.DataBase.MaxDataFileSize")
	valueSize := this.conf.Int64("GooseBuild.DataBase.ValueSize")

	this.staticDB = NewDBBuilder()
	err = this.staticDB.Init(dbPath, int(transformMaxTermCnt), InIdType(maxId),
		uint32(valueSize), uint32(maxIndexFileSize), uint32(maxDataFileSize))
	if err != nil {
		return
	}

	// index strategy global init
	err = indexSty.Init(this.conf)
	if err != nil {
		return
	}

	// static indexer
	this.staticIndexer, err = NewStaticIndexer(this.staticDB, indexSty)
	if err != nil {
		return
	}

	// open data file
	this.fileHd, err = os.OpenFile(toIndexFile, os.O_RDONLY, 0644)
	if err != nil {
		return
	}

	// file iter
	this.fileIter = NewFileIter(this.fileHd)

	return nil
}

func NewGooseBuild() *GooseBuild {
	bui := GooseBuild{}
	return &bui
}
