package patternmatch

import (
	"commonlib/getwe/go-darts"
	logs "commonlib/logs"
	"errors"
)

type extraItem struct {
	// 模板id
	patId int
	// 附加属性
	attr string
}

// 输入wordtree的附加数据
type wordTreeExtra struct {
	itemList []extraItem
}

func newWordTreeExtra() *wordTreeExtra {
	extra := new(wordTreeExtra)
	extra.itemList = make([]extraItem, 0)
	return extra
}

// 输入的单词原文和附加信息
type wordTreeData map[string]*wordTreeExtra

func (wd wordTreeData) insert(word string, patid int, attr string) {
	extra, ok := wd[word]
	if !ok {
		extra := newWordTreeExtra()
		extra.itemList = append(extra.itemList, extraItem{patid, attr})
		wd[word] = extra
		return
	}
	extra.itemList = append(extra.itemList, extraItem{patid, attr})
}

func newWordTreeData() wordTreeData {
	wd := make(map[string]*wordTreeExtra)
	return wd
}

type wordTrieResult struct {
	// 匹配到的一个前缀的长度，以字符rune为单位
	prefixLen int

	// 匹配到的前缀的patId和额外信息
	patId int
	attr  string
}

// 词典树
// 包内结构
type wordTree struct {
	// 单词组成的trie树
	dict *darts.Darts

	// 单词附加信息
	extraInfo []*wordTreeExtra

	log *logs.BeeLogger
}

func newWordTree() *wordTree {
	wt := new(wordTree)
	wt.dict = nil
	wt.extraInfo = make([]*wordTreeExtra, 0)

	wt.log = logs.NewLogger(64)
	wt.log.EnableFuncCallDepth(true)

	return wt
}

func (wt *wordTree) insert(data wordTreeData) error {

	wordData := make(map[string]int)

	for word, extra := range data {
		index := len(wt.extraInfo)

		// 待输入trie树的数据，word->index
		wordData[word] = index
		// 存储额外信息
		// 查找匹配后通过index获取到extrainfo
		wt.extraInfo = append(wt.extraInfo, extra)
		wt.log.Debug("word[%s],index[%d]", word, index)
	}

	// TODO
	// darts.LoadWord(wordData, true) 出现有数据错乱的情况
	dict, err := darts.LoadWord(wordData, false)
	if err != nil {
		return errors.New("darts load word data fail")
	}

	wt.dict = &dict

	return nil
}

func (wt *wordTree) search(word []rune) ([]wordTrieResult, error) {
	res := make([]wordTrieResult, 0)

	trieRes := wt.dict.CommonPrefixSearch(word, 0)
	if len(trieRes) == 0 {
		return res, nil
	}

	for i := 0; i < len(trieRes); i++ {
		index := trieRes[i].Freq

		for _, item := range wt.extraInfo[index].itemList {
			r := wordTrieResult{}
			r.prefixLen = trieRes[i].PrefixLen
			r.patId = item.patId
			r.attr = item.attr

			wt.log.Debug("wt search index[%d],patId[%d]", index, r.patId)
			res = append(res, r)
		}
	}

	return res, nil
}
