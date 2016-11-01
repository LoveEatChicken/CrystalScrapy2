package worddict

import (
	log "commonlib/beegologs"
	darts "commonlib/getwe/go-darts"
)

const (
	SECTION_ATTR_UNKNOWN = 0 // 预留值未知片段,在词典找不到匹配时的默认值
	// 一般建议取值
	SECTION_ATTR_NAME         = 1  // 专名,比较重要的片段
	SECTION_ATTR_KEYWORD      = 2  // 关键词,也很重要,不可省略
	SECTION_ATTR_KEYWORD_OMIT = 3  // 关键词,也很重要,但是可省
	SECTION_ATTR_OMIT         = 10 // 可省词,在这个检索系统中可有可无
)

// word词典查找结果
type WordDictResult struct {
	Section string //
	Attr    int    // 属性,在词典中配置的一个词对应的属性
}

type WordDict struct {
	dict *darts.Darts
}

// 先尝试加载encodeDictPath,如果失败,则读取dictPath明文词典
func NewWordDict(dictPath, encodeDictPath string) (*WordDict, error) {
	td := WordDict{}

	d, err := darts.Load(encodeDictPath)
	if err != nil {
		log.Llog.Warn(err.Error())

		d, err = darts.Import(dictPath, encodeDictPath, false)
		if err != nil {
			log.Llog.Warn(err.Error())
			td.dict = nil
		} else {
			td.dict = &d
		}
	} else {
		td.dict = &d
	}

	return &td, nil
}

// 在词典中搜索query,顺序标记query中每一段的成分
func (this WordDict) MatchDict(query string) []WordDictResult {
	res := make([]WordDictResult, 0)

	// 没有初始化成功
	if this.dict == nil {
		// 把整个query当成一个未知段,效果差一点,程序还能跑
		res = append(res, WordDictResult{query, SECTION_ATTR_UNKNOWN})
		return res
	}

	key := []rune(query)

	length := len(key)

	lastMatchPos := 0
	pos := 0
	for pos < length {
		r := this.dict.CommonPrefixSearch(key[pos:], 0)
		if len(r) > 0 {
			if pos != lastMatchPos {
				section := string(key[lastMatchPos:pos])
				res = append(res, WordDictResult{section, SECTION_ATTR_UNKNOWN})
			}

			maxlen := 0
			maxlenindex := 0
			for i := 0; i < len(r); i++ {
				if r[i].PrefixLen > maxlen {
					maxlen = r[i].PrefixLen
					maxlenindex = i
				}
			}
			offset := pos
			matchlen := r[maxlenindex].PrefixLen
			section := string(key[offset : offset+matchlen])
			res = append(res, WordDictResult{section, r[maxlenindex].Freq})
			pos = pos + maxlen
			lastMatchPos = pos
		} else {
			pos++
		}
	}
	if pos != lastMatchPos {
		section := string(key[lastMatchPos:])
		res = append(res, WordDictResult{section, SECTION_ATTR_UNKNOWN})
	}

	return res
}
