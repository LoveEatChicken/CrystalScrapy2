package patternmatch

import (
	"os"
)

type Slot struct {
	Name  string //槽名
	Value string //槽值
}

// 一条模板及其附加属性
type Pattern struct {
	PatternText string //模板原文
	PatternAttr string //模板属性
}

// 一个成功模板匹配结果
type PatMatchItem struct {
	Pattern
	SlotList []Slot //提取到的槽位信息
}

func NewPatMatchItem() *PatMatchItem {
	item := new(PatMatchItem)
	item.PatternText = ""
	item.PatternAttr = ""
	item.SlotList = make([]Slot, 0)
	return item
}

// 一次模板搜索的结果
type PatMatchResult struct {
	// 可能会命中不同类型的模板
	// 每命中一个模板的结果就是一个PatMatchItem
	Itemlist []*PatMatchItem
}

func NewPatMatchResult() *PatMatchResult {
	res := new(PatMatchResult)
	res.Itemlist = make([]*PatMatchItem, 0)
	return res
}

type PatternDict struct {
	tree *patternTree
}

func NewPatternDict() *PatternDict {
	dict := new(PatternDict)
	dict.tree = newPatternTree()
	return dict
}

// 输入模板，词典，省略词文件构建模板匹配词典
func (dict *PatternDict) Build(patFile, wordFile, ignoreFile string) error {

	patf, err := os.Open(patFile)
	if err != nil {
		return err
	}

	wordf, err := os.Open(wordFile)
	if err != nil {
		return err
	}

	ignoref, err := os.Open(ignoreFile)
	if err != nil {
		return err
	}

	err = dict.tree.build(patf, wordf, ignoref)
	if err != nil {
		return err
	}

	return nil
}

func (dict *PatternDict) Match(query string) *PatMatchResult {
	ctx := newMatchContext(query)
	res := NewPatMatchResult()
	dict.tree.match(ctx, res)
	return res
}
