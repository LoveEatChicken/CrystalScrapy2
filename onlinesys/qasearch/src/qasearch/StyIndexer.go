package main

import (
	log "commonlib/beegologs"
	"commonlib/getwe/config"
	u "commonlib/getwe/utils"
	"commonlib/goose"
	. "commonlib/goose/utils"
	"commonlib/scws4go"
	simplejson "commonlib/simplejson"

	"errors"
	"reflect"
	"runtime"
)

type StyIndexer struct {
	// 共用切词工具
	scws *scws4go.Scws

	// 共用的只读配置信息

	// value内存块大小
	valueSize uint8

	// 各个检索字段权重
	titleBoost   float32
	keywordBoost float32

	// 调权因子权重
	valueBoost []float64
}

// 分析一个doc,返回其中的term列表,Value,Data.(必须保证框架可并发调用ParseDoc)
func (this *StyIndexer) ParseDoc(doc interface{}, context *goose.StyContext) (
	outId OutIdType, termList []TermInDoc, value Value, data Data, err error) {
	// ParseDoc的功能实现需要注意的是,这个函数是可并发的,使用StyIndexer.*需要注意安全

	context = nil
	outId = 0
	termList = nil
	value = nil
	data = nil

	defer func() {
		if r := recover(); r != nil {
			err = u.ErrFmt("%s", r)
		}
	}()

	// 策略假设每一个doc就是一个string
	realValue := reflect.ValueOf(doc)
	docbuf := realValue.String()

	document, err := simplejson.NewJson([]byte(docbuf))
	if err != nil {
		log.Llog.Error(err.Error())
		log.Llog.Debug("%s", docbuf)
		return 0, nil, nil, nil, u.ErrFmt("parse doc as json fail")
	}

	doc_id, err := document.Get("doc_id").String()
	if err != nil {
		log.Llog.Error(err.Error())
		return 0, nil, nil, nil, u.ErrFmt("get doc_id fail")
	}
	DocId, err := u.MD5SignInt32(doc_id)
	if err != nil {
		log.Llog.Error(err.Error())
		return 0, nil, nil, nil, u.ErrFmt("md5 sign to int32 fail")
	}
	log.Llog.Debug("doc_id [%s] -> id [%d]", doc_id, DocId)
	// outid
	outId = OutIdType(DocId)
	log.Llog.Info("outId:%d", DocId)

	// write termInDoc
	termList, err = this.parseTerm(document)
	log.Llog.Info("termCount:%d", len(termList))

	// write value
	value, err = this.parseValue(document)
	if err != nil {
		log.Llog.Warn("parseValue fail : %s", err)
		return
	}

	// write data
	data, err = document.Encode()
	if err != nil {
		log.Llog.Warn("encode cse_data fail : %s", err)
		return
	}

	return
}

// 调用一次初始化
func (this *StyIndexer) Init(conf config.Conf) (err error) {

	// scws初始化
	scwsDictPath := conf.String("Strategy.Indexer.Scws.xdbdict")
	scwsRulePath := conf.String("Strategy.Indexer.Scws.rules")
	scwsForkCnt := runtime.NumCPU()
	this.scws = scws4go.NewScws()
	err = this.scws.SetDict(scwsDictPath, scws4go.SCWS_XDICT_XDB|scws4go.SCWS_XDICT_MEM)
	if err != nil {
		return err
	}
	err = this.scws.SetRule(scwsRulePath)
	if err != nil {
		return err
	}
	this.scws.SetCharset("utf8")
	this.scws.SetIgnore(1)
	this.scws.SetMulti(scws4go.SCWS_MULTI_SHORT & scws4go.SCWS_MULTI_DUALITY & scws4go.SCWS_MULTI_ZMAIN)
	err = this.scws.Init(scwsForkCnt)
	if err != nil {
		return err
	}

	// ValueSize 框架允许写入的最大长度
	this.valueSize = uint8(conf.Int64("GooseBuild.DataBase.ValueSize"))
	if this.valueSize < 1 {
		log.Llog.Error("GooseBuild.DataBase.ValueSize[%d] fail"+
			"at least 1", this.valueSize)
		return errors.New("read conf fail")
	}

	// Weight boost
	this.titleBoost = float32(conf.Float64("Strategy.Indexer.Weight.titleBoost"))
	this.keywordBoost = float32(conf.Float64("Strategy.Indexer.Weight.KeyWordBoost"))
	if this.titleBoost == 0.0 || this.keywordBoost == 0.0 {
		log.Llog.Warn("index weight conf titleBoost[%f] keywordBoost[%f]",
			this.titleBoost, this.keywordBoost)
	}

	this.valueBoost = conf.Float64Array("Strategy.ValueBoost")
	log.Llog.Debug("Strategy.ValueBoost : %v", this.valueBoost)

	if len(this.valueBoost) != 1 {
		log.Llog.Error("Strategy.ValueBoost length must be 4,see parseValue")
		return errors.New("read conf fail")
	}

	return nil
}
