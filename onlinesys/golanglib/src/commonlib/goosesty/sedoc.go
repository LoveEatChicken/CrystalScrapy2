package goosesty

import (
	. "commonlib/goose/utils"

	"errors"
)

// 使用goose做检索排序可通用使用的结果数组
type SeDoc struct {

	// 内部id
	InId InIdType

	// 外部id
	OutId OutIdType

	// 文本相关性得分
	Bweight int

	// 最终调权后相关性得分
	Weight int

	// 聚类id
	// 排序过程对于需要做聚合的,需要离线计算出来同一个ClusterId后进行聚合
	ClusterId uint32

	// 调权字段原始值
	AdjustValue []float64
}

type SeDocArray []SeDoc

// 支持sort包排序
func (v SeDocArray) Len() int {
	return len(v)
}

func (v SeDocArray) Swap(i, j int) {
	v[i], v[j] = v[j], v[i]
}

// 根据Weight排序,用于决定最终排序
type WeightSort struct {
	SeDocArray
}

func (v WeightSort) Less(i, j int) bool {
	if v.SeDocArray[i].Weight > v.SeDocArray[j].Weight {
		return true
	}

	if v.SeDocArray[i].Weight < v.SeDocArray[j].Weight {
		return false
	}

	return v.SeDocArray[i].InId < v.SeDocArray[j].InId
}

// 把相同的clusterid的元素排在一起
// 排序后每一块会保留第一个作为聚类结果
type GroupByClusterId struct {
	SeDocArray
}

func (v GroupByClusterId) Less(i, j int) bool {
	if v.SeDocArray[i].ClusterId > v.SeDocArray[j].ClusterId {
		return true
	}
	if v.SeDocArray[i].ClusterId < v.SeDocArray[j].ClusterId {
		return false
	}
	// OutId一样,说明是相同两个doc多次插入,保留后更新的,即InId比较大的
	if v.SeDocArray[i].OutId == v.SeDocArray[j].OutId {
		return v.SeDocArray[i].InId > v.SeDocArray[j].InId
	}

	// OutId不一样,保留Weight大的
	if v.SeDocArray[i].Weight > v.SeDocArray[j].Weight {
		return true
	}
	if v.SeDocArray[i].Weight < v.SeDocArray[j].Weight {
		return false
	}
	// Weight 也一样,保留先入库的
	return v.SeDocArray[i].InId > v.SeDocArray[j].InId
}

// 利用value数据进行调权
func (doc *SeDoc) AdjustWeight(value Value, valueBoost []float64,
	debug *Debug) error {

	if len(value) != len(valueBoost) {
		return errors.New("value size not equal valueBoost")
	}

	// 解析拿到调权字段
	doc.AdjustValue = make([]float64, len(valueBoost))
	for i := range valueBoost {
		doc.AdjustValue[i] = float64(value[i])
	}

	// 进行调权
	doc.Weight = doc.Bweight
	for i, boost := range valueBoost {
		w := float64(doc.Bweight) * doc.AdjustValue[i] * boost * 0.01
		doc.Weight += int(w)
		debug.AddDocDebugInfo(uint32(doc.InId),
			"adjustWei[%d] = bweight[%d]*adjustvalue[%.3f]*boost[%.3f]*0.01",
			int(w), doc.Bweight, doc.AdjustValue[i], boost)
	}

	return nil
}
