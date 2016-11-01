package goosesty

import (
	"commonlib/scws4go"
	"math"
)

// 一个计算term weight的函数声明
// fieldContent 切词原内容
// term scws4go的切词后的一个term
// segmentCount 切词结果数
// boost调权系数
type CalTermWeightFunc func(fieldContent string, term scws4go.ScwsRes, segmentCount int, boost float32) TermInDocFeature

// 根据长度信息算出一个title类型的term weight
func TitleTermWeiByLen(fieldContent string, term scws4go.ScwsRes, boost float32) TermInDocFeature {
	wei := float32(len(term.Term)) / float32(len(fieldContent))
	if term.Idf > 0 {
		wei += float32(math.Log10(term.Idf))
	}
	return NewTermInDocFeature(0, wei*boost, 0)
}

// 根据长度信息算出一个maintitle类型的term weight
func MainTitleTermWeiByLen(fieldContent string, term scws4go.ScwsRes, boost float32) TermInDocFeature {
	wei := float32(len(term.Term)) / float32(len(fieldContent))
	if term.Idf > 0 {
		wei += float32(math.Log10(term.Idf))
	}
	return NewTermInDocFeature(wei*boost, 0, 0)
}
