package main

import (
	log "commonlib/beegologs"
	. "commonlib/goose/utils"
	sty "commonlib/goosesty"
	json "commonlib/simplejson"

	"commonlib/scws4go"

	//"encoding/binary"
	"math"
	"strings"
)

/*
 */

func (this StyIndexer) extractValue(document *json.Json) (Value, error) {
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

/*
{
  "origin": "法国",
  "composition": "欧洲椴花水甜杏仁油",
  "name": "希思黎植物舒缓面膜  60ml",
  "color": "无",
  "comment_num": "0",
  "price": "$94.0",
  "unit_spec": "60ml",
  "usage": "将脸部洗净后，均匀涂抹于包括眼睛周围在内的整个脸部，15-20分钟后用温水清洗。 根据皮肤类型，取适量爽肤水整理皮肤。",
  "suitabe_skin": "营养面膜",
  "shelf_life": "使用期限为自生产之日起3年，尽可能发送最近生产的产品。"
}
*/

func (this StyIndexer) extractTerm(document *json.Json) ([]TermInDoc, error) {

	termMgr := sty.NewTermInDocMgr()
	this.extractWholeMatchTerm(document, termMgr)
	this.extractTitle(document, termMgr)

	return termMgr.Output(), nil
}

// 分析添加字段全匹配的term
func (this StyIndexer) extractWholeMatchTerm(document *json.Json, termMgr *sty.TermInDocMgr) {

	for i, field := range this.wholeMatchField {
		cont, err := document.Get(field).StringArray()
		if err != nil {
			log.Llog.Warn("[%d] field[%s] is not string", i, field)
			continue
		}
		for _, c := range cont {

			weight := float32(1.0) //满分
			termMgr.AddWholeMatchTerm(c, field, weight)
			log.Llog.Debug("whold match field[%s] cont[%s] weight[%f]", field, c, weight)
		}
	}
}

func (this StyIndexer) extractTitle(doc *json.Json, termMgr *sty.TermInDocMgr) {
	for i, field := range this.titleMatchField {
		cont, err := doc.Get(field).StringArray()
		if err != nil {
			log.Llog.Warn("[%d] field[%s] is not string", i, field)
			continue
		}
		if len(cont) < 1 {
			log.Llog.Warn("[%d] field[%s] is empty array", i, field)
			continue
		}
		title := cont[0]
		boost := float32(0.9)
		this.extractTitleField(field, title, boost, true, termMgr)
	}
}

// 对一个字段按title类来建索引
// field 字段名
// content 字段内容
// boost 权重调整系数
// withFieldSearch 是否支持字段内检索
// f 算term权重的函数
func (this StyIndexer) extractTitleField(field, content string, boost float32, withFieldSearch bool, termMgr *sty.TermInDocMgr) {
	segResult, err := this.scws.Segment(content)
	if err != nil {
		log.Llog.Warn("segment[%s] fail : %s", content, err)
		return
	}

	for _, term := range segResult {
		termStr := strings.ToLower(term.Term)
		termWei := sty.TitleTermWeiByLen(content, term, boost)
		termMgr.AddTerm(termStr, termWei)

		// 支持字段内检索
		if withFieldSearch {
			termMgr.AddTerm(sty.GetFieldMatchTerm(termStr, field), termWei)
		}
	}
}

/*
func (this StyIndexer) extractKeyword(document *json.Json,
	termMgr map[string]sty.TermInDocFeature) {
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

			oldwei, ok := termMgr[termStr]
			newwei := sty.NewTermInDocFeature(0, 0, termWei)
			if ok {
				newwei.Merge(&oldwei)
			}
			termMgr[termStr] = newwei
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
