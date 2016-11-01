package main

import (
	log "commonlib/beegologs"
	. "commonlib/goose/utils"
	sty "commonlib/goosesty"
	simplejson "commonlib/simplejson"

	"commonlib/scws4go"

	//"encoding/binary"
	"math"
	"strings"
)

/*
 */

func (this StyIndexer) parseValue(document *simplejson.Json) (Value, error) {
	// NewValue(len,cap)
	value := NewValue(int(this.valueSize), int(this.valueSize))

	/*
		packageId, err := document.Get("packageId").Int()
		if err != nil {
			return nil, log.Llog.Warn("get packageId as int fail")
		}
		clickLevel, err := document.Get("clickLevel").Int()
		if err != nil {
			return nil, log.Llog.Warn("get clickLevel as int fail")
		}
		downloadLevel, err := document.Get("downloadLevel").Int()
		if err != nil {
			return nil, log.Llog.Warn("get downloadLevel as int fail")
		}
		isOfficial, err := document.Get("isOfficial").Int()
		if err != nil {
			return nil, log.Llog.Warn("get isOfficial as int fail")
		}
		score, err := document.Get("score").Int()
		if err != nil {
			return nil, log.Llog.Warn("get score as int fail")
		}

		order := binary.BigEndian
		// 第一个数字是聚类id,占用4个字节
		order.PutUint32(value[0:4], uint32(packageId))

		// 剩下空间用于写入调权字段
		value[4] = byte(clickLevel)
		value[5] = byte(downloadLevel)
		value[6] = byte(isOfficial)
		value[7] = byte(score)

		// value截掉多余元素
		value = value[:8]
	*/
	value[0] = 0

	return value, nil
}

func (this StyIndexer) parseTerm(document *simplejson.Json) ([]TermInDoc, error) {

	termMgr := sty.NewTermInDocMgr()

	this.parseTitle(document, termMgr)
	// this.parseKeyword(document, termMgr)

	termList := termMgr.Output()

	return termList, nil
}

func (this StyIndexer) parseTitle(document *simplejson.Json, termMgr *sty.TermInDocMgr) {
	title, err := document.Get("question").String()
	if err != nil {
		log.Llog.Warn("get title fail : %s", err)
		return
	}

	segResult, err := this.scws.Segment(title)
	if err != nil {
		log.Llog.Warn("segment[%s] fail : %s", title, err)
		return
	}

	for _, term := range segResult {
		termStr := strings.ToLower(term.Term)
		termWei := this.calTitleTermWei(title, term, this.titleBoost)
		newwei := sty.NewTermInDocFeature(0, termWei, 0)

		termMgr.AddTerm(termStr, newwei)
	}
}

/*
func (this StyIndexer) parseKeyword(document *simplejson.Json,
	termHash map[string]sty.TermInDocFeature) {
	tags, _ := document.Get("tags").String()

	for _, tag := range strings.Split(tags, ";") {

		segResult, err := this.scws.Segment(tag)
		if err != nil {
			log.Llog.Warn("segment[%s] fail : %s", tag, err)
			return
		}

		for _, term := range segResult {
			termStr := strings.ToLower(term.Term)
			termWei := this.calKeywordTermWei(tag, term, this.keywordBoost)

			oldwei, ok := termHash[termStr]
			newwei := sty.NewTermInDocFeature(0, 0, termWei)
			if ok {
				newwei.Merge(&oldwei)
			}
			termHash[termStr] = newwei
		}
	}
}
*/

// 根据title,切词得到的term,权重因子计算term在doc中的重要性
func (this StyIndexer) calTitleTermWei(title string, term scws4go.ScwsRes, boost float32) float32 {
	wei := float32(len(term.Term)) / float32(len(title))
	if term.Idf > 0 {
		wei += float32(math.Log10(term.Idf))
	}

	return wei * boost * 1.0
}

func (this StyIndexer) calKeywordTermWei(keyword string, term scws4go.ScwsRes, boost float32) float32 {
	wei := float32(len(term.Term)) / float32(len(keyword))
	if term.Idf > 0 {
		wei += float32(math.Log10(term.Idf))
	}

	return wei * boost * 0.5
}
