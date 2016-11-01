package goose

import (
	"commonlib/getwe/config"
	. "commonlib/goose/database"
	. "commonlib/goose/utils"

	"commonlib/bufferlog"
	se "gorpcimp/search"
)

type StyContext struct {
	// 供策略打日志使用
	Log *bufferlog.BufferLogger
}

// 创建新的
func NewStyContext() *StyContext {
	c := StyContext{}
	c.Log = bufferlog.NewBufferLogger()
	return &c
}

// 克隆,能复用的尽量复用
func (this *StyContext) Clone() *StyContext {
	newc := StyContext{}
	// log不能复用(没必要复用)
	//newc.Log = log.NewGooseLogger()
	// 其它

	return &newc
}

// 重置后可以重用
func (this *StyContext) Clear() {
	//this.Log = log.NewGooseLogger()
}

// 建索引策略.
// 框架会调用一次Init接口进行初始化,建索引的时候会N个goroutine调用ParseDoc
type IndexStrategy interface {
	// 全局初始化的接口
	Init(conf config.Conf) error

	// 分析一个doc,返回其中的term列表,Value,Data
	ParseDoc(doc interface{}, context *StyContext) (OutIdType, []TermInDoc, Value, Data, error)
}

type SearchStrategy interface {
	// 全局初始化的接口
	Init(conf config.Conf) error

	// 解析请求
	// 返回term列表,一个由策略决定的任意数据,后续接口都会透传
	ParseQuery(request *se.SeRequest, context *StyContext) ([]TermInQuery, interface{}, error)

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
	CalWeight(queryInfo interface{}, inId InIdType, outId OutIdType,
		termInQuery []TermInQuery, termInDoc []TermInDoc,
		termCnt uint32, context *StyContext) (TermWeight, error)

	/*
	   // 对结果拉链进行过滤
	   Filt(queryInfo interface{},list SearchResultList,context *StyContext) (error)

	   // 结果调权
	   // 确认最终结果列表排序
	   Adjust(queryInfo interface{},list SearchResultList,db ValueReader,context *StyContext) (error)

	   // 构建返回包
	   Response(queryInfo interface{},list SearchResultList,
	       db DataBaseReader,response []byte,context *StyContext) (reslen int,err error)
	*/

	// 合并三个最初的接口(Filt,Adjust,Response)为一个
	// 划分的几个接口,只是给策略增加不必要的麻烦,修改全部开放给策略自定义实现
	Response(queryInfo interface{},
		list SearchResultList,
		valueReader ValueReader,
		dataReader DataReader,
		context *StyContext) (*se.SeResponse, error)
}

/* vim: set expandtab ts=4 sw=4 sts=4 tw=100: */
