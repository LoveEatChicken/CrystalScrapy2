package goose

import (
	log "commonlib/beegologs"
	. "commonlib/goose/database"
	. "commonlib/goose/utils"
	"fmt"

	se "gorpcimp/search"
)

type Searcher struct {
	// 只读数据库
	db DataBaseReader

	// 检索策略逻辑
	strategy SearchStrategy
}

func (this *Searcher) Search(context *StyContext, request *se.SeRequest) (*se.SeResponse, error) {

	// 解析请求
	termInQList, queryInfo, err := this.strategy.ParseQuery(request, context)
	if err != nil {
		return nil, err
	}

	// 构建查询树
	me, err := NewMergeEngine(this.db, termInQList)
	if err != nil {
		return nil, err
	}

	result := make([]SearchResult, 0, GOOSE_DEFAULT_SEARCH_RESULT_CAPACITY)

	// term命中doc的情况
	termInDocList := make([]TermInDoc, len(termInQList))
	var allfinish bool = false

	for allfinish != true {
		var inId InIdType
		var currValid bool

		inId, currValid, allfinish = me.Next(termInDocList)
		if currValid != true {
			continue
		}

		outId, err := this.db.GetOutID(inId)
		if err != nil {
			log.Llog.Warn(fmt.Sprintf("GetOutId fail [%s] InId[%d] OutId[%d]", err, inId, outId))
			continue
		}

		if inId == 0 || outId == 0 {
			log.Llog.Warn(fmt.Sprintf("MergeEngine get illeagl doc InId[%d] OutId[%d]", inId, outId))
			continue
		}

		weight, err := this.strategy.CalWeight(queryInfo, inId, outId,
			termInQList, termInDocList, uint32(len(termInQList)), context)
		if err != nil {
			log.Llog.Warn(fmt.Sprintf("CalWeight fail %s", err.Error()))
			continue
		}

		result = append(result, SearchResult{
			InId:   inId,
			OutId:  outId,
			Weight: weight})

	}

	// 完成
	return this.strategy.Response(queryInfo, result, this.db, this.db, context)
}

func NewSearcher(db DataBaseReader, sty SearchStrategy) (*Searcher, error) {
	var s Searcher
	s.db = db
	s.strategy = sty
	return &s, nil
}

/* vim: set expandtab ts=4 sw=4 sts=4 tw=100: */
