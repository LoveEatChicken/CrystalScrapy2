package goosesty

import (
	. "commonlib/goose/utils"
	"encoding/binary"
	"math"
	"strings"
)

// term在doc中的特征
type TermInDocFeature struct {
	// 命中mainTitle的权值
	MainTitleWeight float32
	// 命中title的权值
	TitleWeight float32
	// 命中keyword的权值
	KeyWordWeight float32
}

// 压缩成goose定义的TermWeight
func (t *TermInDocFeature) Encode() TermWeight {
	order := binary.BigEndian

	buf := make([]byte, 4)
	if t.MainTitleWeight > 1.0 {
		t.MainTitleWeight = 1.0
	}
	if t.TitleWeight > 1.0 {
		t.TitleWeight = 1.0
	}
	if t.KeyWordWeight > 1.0 {
		t.KeyWordWeight = 1.0
	}
	buf[0] = byte(t.MainTitleWeight * math.MaxUint8)
	buf[1] = byte(t.TitleWeight * math.MaxUint8)
	buf[2] = byte(t.KeyWordWeight * math.MaxUint8)
	buf[3] = 0 //暂时没使用

	return TermWeight(order.Uint32(buf))
}

// 从goose的TermWeight解压出实际数据
func (t *TermInDocFeature) Decode(w TermWeight) {
	order := binary.BigEndian

	buf := make([]byte, 4)
	order.PutUint32(buf, uint32(w))

	t.MainTitleWeight = float32(buf[0]) / math.MaxUint8
	t.TitleWeight = float32(buf[1]) / math.MaxUint8
	t.KeyWordWeight = float32(buf[2]) / math.MaxUint8
}

// 合并两个term,权重保留大的值
func (t *TermInDocFeature) Merge(r *TermInDocFeature) {
	if t.MainTitleWeight < r.MainTitleWeight {
		t.MainTitleWeight = r.MainTitleWeight
	}
	if t.TitleWeight < r.TitleWeight {
		t.TitleWeight = r.TitleWeight
	}
	if t.KeyWordWeight < r.KeyWordWeight {
		t.KeyWordWeight = r.KeyWordWeight
	}
}

func NewTermInDocFeature(mainTitle, title, keyowrd float32) TermInDocFeature {
	t := TermInDocFeature{}
	t.MainTitleWeight = mainTitle
	t.TitleWeight = title
	t.KeyWordWeight = keyowrd
	return t
}

type TermInDocMgr struct {
	hash map[string]TermInDocFeature
}

func NewTermInDocMgr() *TermInDocMgr {
	m := new(TermInDocMgr)
	m.hash = make(map[string]TermInDocFeature)
	return m
}

// 为term添加一个新的权重信息
func (m *TermInDocMgr) AddTerm(termStr string, newwei TermInDocFeature) {
	termStr = strings.ToLower(termStr)
	oldwei, ok := m.hash[termStr]
	if ok {
		newwei.Merge(&oldwei)
	}
	m.hash[termStr] = newwei
}

// 增加一个全匹配term,直接给maintitle
func (m *TermInDocMgr) AddWholeMatchTerm(term, field string, weight float32) {
	t := GetWholeMatchTerm(term, field)
	w := NewTermInDocFeature(weight, 0, 0) // 这种特殊term可以认为最高权重
	m.AddTerm(t, w)
}

// 增加一个字段内匹配的term,直接给maintitle
func (m *TermInDocMgr) AddFieldMatchTerm(term, field string, weight float32) {
	t := GetFieldMatchTerm(term, field)
	w := NewTermInDocFeature(weight, 0, 0)
	m.AddTerm(t, w)
}

// 压缩成goose框架内部的term表示
func (m *TermInDocMgr) Output() []TermInDoc {
	termList := make([]TermInDoc, 0, len(m.hash))
	for k, v := range m.hash {
		termList = append(termList, TermInDoc{
			Sign:   TermSign(StringSignMd5(k)),
			Weight: v.Encode()})
	}
	return termList
}
