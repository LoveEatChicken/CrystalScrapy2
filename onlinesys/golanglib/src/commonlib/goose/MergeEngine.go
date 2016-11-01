package goose

import (
	log "commonlib/beegologs"
	. "commonlib/goose/database"
	. "commonlib/goose/utils"
	"container/heap"

	u "commonlib/getwe/utils"
)

type listMinHeapItem struct {
	sign TermSign // term签名
	no   int      // term编号
	list *InvList // term对应拉链
	pos  int      // 当前遍历到位置
	omit int      // term是否可省.0表示可省,大于0表示不可省.
	// 不可省需赋值为1<<no,可以表示第no个term不可省
}

// 当前遍历到的元素
func (this *listMinHeapItem) Curr() Index {
	return (*this.list)[this.pos]
}

// 开始遍历下一个元素,如果结束返回false
func (this *listMinHeapItem) Next() bool {
	// 后移一个元素
	this.pos++

	// this.pos == len(*this.list) 表示拉链遍历完
	// 操作list[pos]是非法的

	if this.pos < len(*this.list) {
		return true
	}
	return false
}

type listMinHeap []listMinHeapItem

// 堆必须支持接口:Len
func (ih listMinHeap) Len() int {
	return len(ih)
}

// 堆排序必须支持接口:Less
func (ih listMinHeap) Less(i, j int) bool {
	indexa := ih[i].pos
	indexb := ih[j].pos
	// InID小的先归并
	return (*ih[i].list)[indexa].InID < (*ih[j].list)[indexb].InID
}

// 堆排序必须支持接口:Swap
func (ih listMinHeap) Swap(i, j int) {
	ih[i], ih[j] = ih[j], ih[i]
}

// 堆排序必须支持接口:Push
func (ih *listMinHeap) Push(x interface{}) {
	*ih = append(*ih, x.(listMinHeapItem))
}

// 堆排序必须支持接口:Pop
func (ih *listMinHeap) Pop() interface{} {
	old := *ih
	n := len(old)
	item := old[n-1]
	*ih = old[0 : n-1]
	return item
}

func (ih listMinHeap) Top() interface{} {
	return ih[0]
}

type MergeEngine struct {
	lstheap   *listMinHeap // 归并用最小堆
	omitflag  int          // 不可省term的标记
	termCount int
}

func NewMergeEngine(db DataBaseReader, termList []TermInQuery) (*MergeEngine, error) {
	mg := MergeEngine{}
	if len(termList) >= GOOSE_MAX_QUERY_TERM {
		return nil, u.ErrFmt("to much terms [%d]", len(termList))
	}

	mg.omitflag = 0
	mg.lstheap = &listMinHeap{}
	mg.termCount = len(termList)
	heap.Init(mg.lstheap)

	// 把全部拉链建成小顶堆
	for i, e := range termList {
		var err error
		item := listMinHeapItem{}

		item.list, err = db.ReadIndex(e.Sign)
		if err != nil {
			log.Llog.Warn("read term[%d] : %s", e.Sign, err)
			item.list = nil
		}
		item.no = i
		item.pos = 0
		item.sign = e.Sign
		if e.CanOmit {
			item.omit = 0 // 0表示可省
		} else {
			item.omit = 1 << uint(i) // 不可省term
		}

		// 拉链有效才放入堆
		if item.list != nil && item.list.Len() > 0 {
			heap.Push(mg.lstheap, item)
		}

		// 同时记下不可省term的标记
		if e.CanOmit == false {
			mg.omitflag ^= 1 << uint(i)
		}

		log.Llog.Debug("term[%d] omit[%d] weight[%d] listLen[%d]", item.sign,
			item.omit, e.Weight, len(*item.list))
	}

	log.Llog.Debug("termCnt[%d] omitflag[%d]", mg.termCount, mg.omitflag)

	return &mg, nil
}

func (this *MergeEngine) Next(termInDoclist []TermInDoc) (inId InIdType, currValid, allfinish bool) {

	if len(termInDoclist) != this.termCount {
		log.Llog.Warn("len(termInDoclist) != this.termCount")
		return 0, false, true
	}

	if this.lstheap.Len() == 0 {
		return 0, false, true
	}

	// 初始化
	for i, _ := range termInDoclist {
		termInDoclist[i].Sign = 0
		termInDoclist[i].Weight = 0
	}
	oflag := 0

	/*
	   // 先看当前id最小的堆顶
	   item := this.lstheap.Pop().(listMinHeapItem)
	   currInID := item.Curr().InID

	   // 记下当前doc
	   termInDoclist[ item.no ].Sign = item.sign
	   termInDoclist[ item.no ].Weight = item.Curr().Weight
	   oflag ^= item.omit
	*/

	top := this.lstheap.Top().(listMinHeapItem)
	currInID := top.Curr().InID

	currValid = true
	allfinish = false

	for this.lstheap.Len() > 0 {
		top := this.lstheap.Top().(listMinHeapItem)

		if top.Curr().InID != currInID {
			// 遇到新的doc了,就是归并完一个doc
			// 跳出去校验currInID的命中情况
			break
		}

		// 堆里面还有相同的doc,先弹出
		item := heap.Pop(this.lstheap).(listMinHeapItem)

		// 记下当前doc
		termInDoclist[item.no].Sign = item.sign
		termInDoclist[item.no].Weight = item.Curr().Weight
		oflag ^= item.omit

		// 如果拉链没遍历完,继续加入堆
		if item.Next() {
			heap.Push(this.lstheap, item)
		} else {
			// 如果拉链遍历完,且这个拉链是不可省term
			// 处理完当前doc后后面不需要再归并了
			if item.omit > 0 {
				allfinish = true
				log.Llog.Debug("not omit item travel end no[%d] pos[%d] list.len[%d]",
					item.no, item.pos, len(*item.list))
			}
		}
	}

	// 检查不可省term是否有全部命中
	if oflag != this.omitflag {
		// 这次归并得到的doc没有用,丢掉吧
		currValid = false
	} else {
		currValid = true
	}

	inId = currInID
	return
}
