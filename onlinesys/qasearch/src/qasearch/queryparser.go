package main

import (
	log "commonlib/beegologs"
	sty "commonlib/goosesty"
	wd "commonlib/worddict"
	se "gorpcimp/search"

	. "commonlib/goose"
	. "commonlib/goose/utils"

	"math"
	"strings"
)

// 本地辅助计算用
type queryTerm struct {
	term   string
	idf    float64
	weight float32
	attr   int
	omit   bool
}

func (this StySearcher) parseQuery(request *se.SeRequest,
	context *StyContext, styData *strategyData) ([]TermInQuery, error) {

	styData.query = strings.ToLower(request.Query)
	styData.isdebug = request.IsDebug
	styData.pageNum = int(request.PageNum)
	styData.pageSize = int(request.PageSize)
	styData.debug = sty.NewDebug(styData.isdebug)

	context.Log.Info("query", styData.query)
	context.Log.Info("pageNum", styData.pageNum)
	context.Log.Info("pageSize", styData.pageSize)

	termarr := make([]queryTerm, 0)
	log.Llog.Debug("query[%s]", styData.query)
	// 先对query进行分段
	// 分词上首先尊重策略自定义的词典
	dictRes := this.wordDict.MatchDict(styData.query)
	// 对每一段进行切词
	for _, s := range dictRes {
		log.Llog.Debug("section[%s] attr[%d]", s.Section, s.Attr)
		segResult, err := this.scws.Segment(s.Section)
		if err != nil {
			log.Llog.Warn(err.Error())
			continue
		}
		for _, t := range segResult {
			termarr = append(termarr, queryTerm{
				attr: s.Attr, // term的属性取的是trie的配置,而不是scws4go自带
				idf:  t.Idf,
				term: t.Term})
			log.Llog.Debug("section[%s] term[%s]", s.Section, t.Term)
		}

	}
	return this.calQueryTerm(context, styData, termarr)
}

// 根据Query,Query的切词结果,Query在trie词典的匹配情况以及查找到的属性
// 计算term重要性,是否可省
func (this StySearcher) calQueryTerm(context *StyContext, styData *strategyData,
	termarr []queryTerm) ([]TermInQuery, error) {

	querylen := float32(len(styData.query))

	weightsum := float32(0.0)

	for i, t := range termarr {
		// 根据term的长度算出重要性
		termarr[i].weight = float32(len(t.term)) / querylen

		// 利用scws4go的idf信息进行调整
		if t.idf > 1.0 {
			termarr[i].weight += float32(math.Log10(t.idf))
		}

		// 利用wordDict配置的词属性调整权重
		switch t.attr {
		case wd.SECTION_ATTR_NAME:
			// 专名,最重要的东西
			termarr[i].weight *= 1.5
			termarr[i].omit = false
		case wd.SECTION_ATTR_KEYWORD:
			termarr[i].weight *= 1.1
			termarr[i].omit = false
		case wd.SECTION_ATTR_KEYWORD_OMIT:
			termarr[i].weight *= 1.0
			termarr[i].omit = true
		case wd.SECTION_ATTR_OMIT:
			// 可省词降低权重
			termarr[i].weight *= 0.1
			termarr[i].omit = true
		case wd.SECTION_ATTR_UNKNOWN:
			termarr[i].weight *= 0.3
			termarr[i].omit = true
		}

		weightsum += termarr[i].weight
	}

	termList := make([]TermInQuery, len(termarr), len(termarr))
	for i, t := range termarr {
		termList[i].Sign = TermSign(StringSignMd5(strings.ToLower(t.term)))
		termList[i].CanOmit = t.omit
		termList[i].SkipOffset = true
		termList[i].Attr = uint32(t.attr)
		//weight权值是[0,1]乘上MaxUint16保存,后续要用需要除于MaxUint16还原
		wei := t.weight / weightsum
		termList[i].Weight = TermWeight(wei * math.MaxUint16)

		{
			log.Llog.Debug("term[%s] omit[%v] weight[%0.4f]",
				strings.ToLower(t.term),
				t.omit,
				wei)

			styData.debug.AddDebugInfo("term[%s] attr[%d] omit[%v] weight[%0.4f]",
				strings.ToLower(t.term),
				t.attr,
				t.omit,
				wei)
		}
	}

	return termList, nil
}
