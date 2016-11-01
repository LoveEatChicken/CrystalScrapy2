package main

import (
	"commonlib/getwe/config"
	. "commonlib/goose"
	. "commonlib/goose/database"
	. "commonlib/goose/utils"
	"commonlib/scws4go"

	"errors"
	"runtime"
	"sort"

	log "commonlib/beegologs"
	u "commonlib/getwe/utils"
	sty "commonlib/goosesty"
	wd "commonlib/worddict"
	se "gorpcimp/search"
)

// 策略的自定义临时数据
type strategyData struct {
	query    string
	pageNum  int
	pageSize int

	isdebug bool

	debug *sty.Debug
}

// 检索的时候,goose框架收到一个完整的网络请求便认为是一次检索请求.
// 框架把收到的整个网络包都传给策略,不关心具体的检索协议.
type StySearcher struct {
	scws *scws4go.Scws

	wordDict *wd.WordDict

	valueBoost []float64
}

// 全局调用一次初始化策略
func (this *StySearcher) Init(conf config.Conf) (err error) {
	// scws初始化
	scwsDictPath := conf.String("Strategy.Searcher.Scws.xdbdict")
	scwsRulePath := conf.String("Strategy.Searcher.Scws.rules")
	scwsForkCnt := runtime.NumCPU()

	log.Llog.Debug("Searcher Strategy Init. scws dict[%s] rule[%s] cpu[%d]",
		scwsDictPath, scwsRulePath, scwsForkCnt)

	this.scws = scws4go.NewScws()
	err = this.scws.SetDict(scwsDictPath, scws4go.SCWS_XDICT_XDB|scws4go.SCWS_XDICT_MEM)
	if err != nil {
		return
	}
	err = this.scws.SetRule(scwsRulePath)
	if err != nil {
		return
	}
	this.scws.SetCharset("utf8")
	this.scws.SetIgnore(1)
	this.scws.SetMulti(scws4go.SCWS_MULTI_SHORT & scws4go.SCWS_MULTI_DUALITY & scws4go.SCWS_MULTI_ZMAIN)
	err = this.scws.Init(scwsForkCnt)
	if err != nil {
		return
	}

	// treedict
	WordDictDataPath := conf.String("Strategy.Searcher.WordDict.DataFile")
	WordDictPath := conf.String("Strategy.Searcher.WordDict.DictFile")
	this.wordDict, _ = wd.NewWordDict(WordDictDataPath, WordDictPath)

	/*
		// AdjustWeightFieldCount
		this.adjustWeightFieldCount = uint8(conf.Int64("Strategy.AdjustWeightFieldCount"))
			// 允许没有调权
			if this.adjustWeightFieldCount == 0 {
				return log.Error("AdjustWeightFieldCount[%d] illegal",
					this.adjustWeightFieldCount)
			}
	*/

	// valueBoost 调权参数权重
	this.valueBoost = conf.Float64Array("Strategy.ValueBoost")
	log.Llog.Debug("Strategy.ValueBoost : %v", this.valueBoost)

	if len(this.valueBoost) != 1 {
		log.Llog.Error("Strategy.ValueBoost length must be 1,see parseValue")
		return errors.New("Strategy Init fail")
	}

	return
}

// 解析请求
// 返回term列表,一个由策略决定的任意数据,后续接口都会透传
func (this *StySearcher) ParseQuery(request *se.SeRequest,
	context *StyContext) ([]TermInQuery, interface{}, error) {

	// 策略在多个接口之间传递的数据
	styData := &strategyData{}

	// 解析命令
	termInQuery, err := this.parseQuery(request, context, styData)
	if err != nil {
		return nil, nil, err
	}
	return termInQuery, styData, nil
}

// 对一个结果进行打分,确定相关性
// queryInfo    : ParseQuery策略返回的结构
// inId         : 需要打分的doc的内部id
// outId        : 需求打分的doc的外部id
// termInQuery  : 所有term在query中的打分
// termInDoc    : 所有term在doc中的打分
// termCnt      : term数量
// Weight       : 返回doc的相关性得分
// 返回错误当前结果则丢弃
// @NOTE query中的term不一定能命中doc,TermInDoc.Weight == 0表示这种情况
func (this *StySearcher) CalWeight(queryInfo interface{}, inId InIdType,
	outId OutIdType, termInQuery []TermInQuery, termInDoc []TermInDoc,
	termCnt uint32, context *StyContext) (TermWeight, error) {

	styData := queryInfo.(*strategyData)
	if styData == nil {
		return 0, errors.New("StrategyData nil")
	}

	queryMatch := this.queryMatch(styData, inId, termInQuery, termInDoc)
	docMatch := this.docMatch(styData, inId, termInQuery, termInDoc)
	omitPunish := this.omitTermPunish(styData, inId, termInQuery, termInDoc)

	weight := queryMatch * docMatch * omitPunish

	styData.debug.AddDocDebugInfo(uint32(inId),
		"bweight[%.3f] = queryMatch[%.3f] * docMatch[%.3f] * omitPunish[%.3f]",
		weight, queryMatch, docMatch, omitPunish)

	return TermWeight(weight * 100 * 100), nil
}

// 构建返回包
func (this *StySearcher) Response(queryInfo interface{},
	list SearchResultList,
	valueReader ValueReader,
	dataReader DataReader,
	context *StyContext) (*se.SeResponse, error) {
	/*
	   // from goose
	   type SearchResult struct {
	       InId    InIdType
	       OutId   OutIdType
	       Weight  TermWeight
	   }
	*/

	styData := queryInfo.(*strategyData)
	if styData == nil {
		return nil, errors.New("StrategyData nil")
	}

	// 策略自己定义的拉链
	stylist := make([]sty.SeDoc, 0, len(list))
	for _, e := range list {
		stylist = append(stylist, sty.SeDoc{
			InId:    e.InId,
			OutId:   e.OutId,
			Bweight: int(e.Weight),
		})
	}

	// 对拉链加载解析Value ( 应该是耗时操作 )
	for i := 0; i < len(stylist); i++ {
		// 耗时操作：读取value数据
		value, err := valueReader.ReadValue(stylist[i].InId)
		if err != nil {
			log.Llog.Warn(err.Error())
			return nil, u.ErrFmt("ReadValue[%d] InId[%d] fail", i, stylist[i].InId)
		}
		// 调权
		err = stylist[i].AdjustWeight(value, this.valueBoost, styData.debug)
		if err != nil {
			log.Llog.Warn(err.Error())
			return nil, u.ErrFmt("[%d] InId[%d] Adjust fail", i, stylist[i].InId)
		}
	}

	// 类聚去重,qasearch不需要

	// 根据Weight做最终排序
	sort.Sort(sty.WeightSort{stylist})

	return this.buildRes(styData, stylist, dataReader, context)
}

// 构建返回包
func (this *StySearcher) buildRes(styData *strategyData, list sty.SeDocArray,
	db DataReader, context *StyContext) (*se.SeResponse, error) {
	log.Llog.Debug("in Response Strategy")

	// 分页
	begin := styData.pageNum * styData.pageSize
	if begin > len(list) {
		begin = len(list)
	}
	end := begin + styData.pageSize
	if end > len(list) {
		end = len(list)
	}
	retlist := list[begin:end]
	log.Llog.Debug("result list len[%d] range [%d:%d]", len(list), begin, end)

	response := new(se.SeResponse)
	response.RetNum = int32(len(retlist))
	response.DispNum = int32(len(list))
	response.ResList = make([]*se.SeDoc, len(retlist), len(retlist))

	tmpData := NewData()

	for i, rdoc := range retlist {

		err := db.ReadData(rdoc.InId, &tmpData)
		if err != nil {
			log.Llog.Warn("ReadData fail[%s] InId[%d] OutId[%d]", err.Error(),
				rdoc.InId, rdoc.OutId)
			continue
		}

		doc := new(se.SeDoc)
		doc.Bweight = int32(rdoc.Bweight)
		doc.Weight = int32(rdoc.Weight)
		doc.Data = string(tmpData)

		if styData.isdebug {
			doc.Debug = styData.debug.GetDocDebugInfoJoin(uint32(rdoc.InId), "\n")
		}

		log.Llog.Debug("retdoc[%d] bweight[%d] weight[%d]",
			i, doc.Bweight, doc.Weight)

		response.ResList[i] = doc
	}

	if styData.isdebug {
		response.Debug = styData.debug.GetDebugInfoJoin("\n")
	}

	return response, nil

}
