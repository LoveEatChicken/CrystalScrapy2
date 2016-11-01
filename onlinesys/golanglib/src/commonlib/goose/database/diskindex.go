package database

import (
	u "commonlib/getwe/utils"
	. "commonlib/goose/utils"

	"encoding/binary"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

const (
	// DiskIndex中一级索引块大小
	Index1BolckNum = 1024
)

// DiskIndex 的两种状态路线.
//  * 打开后只读 : DiskIndexInit --> DiskIndexReadOnly --> DiskIndexClose.
//  * 打开后只写 : DiskIndexInit --> DiskIndexWriteOnly --> DiskIndexClose.
const (
	DiskIndexInit      = "DiskIndexInit"
	DiskIndexReadOnly  = "DiskIndexReadOnly"
	DiskIndexWriteOnly = "DiskIndexWriteOnly"
	DiskIndexClose     = "DiskIndexClose"
)

// 磁盘索引的一些附加信息.
type DiskIndexStatus struct {
	// 最大索引数量
	MaxTermCount int64

	// 实际索引数量
	TermCount int64
}

// 磁盘索引.只支持一次性写入后只读操作.
type DiskIndex struct {
	JsonStatusFile
	// 磁盘存储目录
	filePath string

	// 文件名称
	fileName string

	// 写操作互斥
	lock sync.RWMutex

	// 索引状态信息
	diskStatus DiskIndexStatus

	// 索引状态(这个不能也不应该持久化存储在磁盘)
	indexStatus string

	// 当前term总数
	// 在只读索引中应该等于DiskIndexStatus.TermCount
	// 在只写索引(建库阶段)表示当前已经写入的term数量
	currTermCount int64

	// 零级索引(定长)
	// 一级索引按块组织,每个快包含Index1BlockNum个term
	// 每个块的第一个term组成一个*升序*常驻内存数组
	index0 []TermSign

	// 一级索引(定长)
	// 全部termSign组成的*升序*数组[termSign][termSign]
	index1 *MmapFile

	// 二级索引(定长)
	// 三季索引的索引BigFileIndex:{FileNo,Offset,Length}
	index2 *os.File

	// 三级索引(变长)
	// 根据{FileNo,Offset,Length}拉出一整块[]byte
	index3 *BigFile
}

// 磁盘索引一级索引遍历器
type DiskIndexIterator struct {
	currTermCnt int64
	diskindex   *DiskIndex
}

// 获取下一个term,遍历结束返回0
func (this *DiskIndexIterator) Next() TermSign {
	this.currTermCnt++
	if this.diskindex == nil {
		return TermSign(0)
	}
	if this.currTermCnt >= this.diskindex.diskStatus.TermCount {
		return TermSign(0)
	}
	var currTerm TermSign
	currTermSize := uint32(binary.Size(currTerm))

	tmp, _ := this.diskindex.index1.ReadNum(uint32(this.currTermCnt)*currTermSize, currTermSize)
	return TermSign(tmp)
}

// 创建新的迭代器.在返回的迭代器生命有效期间,DiskIndex必须有效
func (this *DiskIndex) NewIterator() IndexIterator {
	i := DiskIndexIterator{}
	i.currTermCnt = -1
	i.diskindex = this
	return &i
}

func (this *DiskIndex) readIndex0(t TermSign) int {
	// 简单二分查找
	var mid int = 0
	var low int = 0
	var high int = len(this.index0) - 1
	for low <= high {
		mid = (low + high) / 2
		if t > this.index0[mid] {
			low = mid + 1
		} else if t < this.index0[mid] {
			high = mid - 1
		} else {
			// 直接在零级索引找到
			// TODO 进一步优化可以免去查一级索引
			return mid
		}
	}
	// 所在的t应该在high这个块内,需要进一步查找一级索引
	return high
}

func (this *DiskIndex) readIndex1(t TermSign) int {
	// 查找零级索引,确认term放在哪个block里面
	blockNum := this.readIndex0(t)
	if blockNum == -1 {
		return blockNum
	}

	// 再在块内进行二分查找[low,high]
	low := blockNum * Index1BolckNum
	high := low + Index1BolckNum - 1
	if high > int(this.diskStatus.TermCount)-1 {
		high = int(this.diskStatus.TermCount) - 1
	}

	var currTerm TermSign
	currTermSize := uint32(binary.Size(currTerm))

	for low <= high {
		mid := (low + high) / 2
		tmp, _ := this.index1.ReadNum(uint32(mid)*currTermSize, currTermSize)
		currTerm = TermSign(tmp)

		if t > currTerm {
			low = mid + 1
		} else if t < currTerm {
			high = mid - 1
		} else {
			return mid
		}
	}
	return -1
}

func (this *DiskIndex) readIndex2(t TermSign) (*BigFileIndex, error) {
	// 先查一级索引
	index1 := this.readIndex1(t)
	if index1 == -1 {
		return nil, errors.New("readIndex1 term Not Found")
	}

	var bigFileI BigFileIndex

	dataLen := binary.Size(bigFileI)
	filePos := index1 * dataLen

	// 读二级索引,确定倒排拉链在BigFile中的存储位置
	buf := make([]byte, dataLen)
	n, err := this.index2.ReadAt(buf, int64(filePos))
	if err != nil || n != len(buf) {
		return nil, err
	}

	err = bigFileI.Decode(buf)
	if err != nil {
		return nil, err
	}

	return &bigFileI, nil
}

func (this *DiskIndex) readIndex3(t TermSign) (*InvList, error) {
	// 查二级索引
	bigFileI, err := this.readIndex2(t)
	if err != nil {
		return nil, err
	}

	// TODO 读索引会进行一次内存分配,后续可以优化由外面传递一个buf进来
	buff := make([]byte, bigFileI.Length)
	err = this.index3.Read(*bigFileI, buff)
	if err != nil {
		return nil, err
	}

	// 把二进制buf根据gob协议反序列化为InvList
	var list InvList
	err = GobDecode(buff, &list)
	if err != nil {
		return nil, err
	}

	return &list, nil
}

func (this *DiskIndex) writeIndex1(t TermSign) error {
	currTermSize := uint32(binary.Size(t))
	fileOff := uint32(this.currTermCount) * currTermSize
	// BUG(honggengwei):把TermSign强制转成int64了
	return this.index1.WriteNum(fileOff, int64(t))
}

func (this *DiskIndex) writeIndex2(t TermSign, bigFileI *BigFileIndex) error {
	dataLen := binary.Size(*bigFileI)
	filePos := this.currTermCount * int64(dataLen)

	buf := make([]byte, dataLen)
	// 写入buf
	err := bigFileI.Encode(buf)
	if err != nil {
		return err
	}

	// 写入二级索引
	n, err := this.index2.WriteAt(buf, int64(filePos))
	if err != nil || n != len(buf) {
		return err
	}
	return this.writeIndex1(t)
}

func (this *DiskIndex) writeIndex3(t TermSign, l *InvList) error {
	// 先对InvList进行序列化
	binBuf, err := GobEncode(*l)
	if err != nil {
		return err
	}

	// 写入bigfile
	bigFileI, err := this.index3.Append(binBuf)
	if err != nil {
		return err
	}

	// 写入二级索引
	return this.writeIndex2(t, bigFileI)
}

// 读取索引,每次查询在内部分配一块内存返回
func (this *DiskIndex) ReadIndex(t TermSign) (*InvList, error) {
	// 读取不加锁

	// 打开的磁盘只读索引下才允许读取
	if this.indexStatus != DiskIndexReadOnly {
		return nil, errors.New("DiskIndex.Read status error")
	}
	return this.readIndex3(t)
}

// 写入索引,内部加锁保证顺序写入.
// 同一个term多次写入,会进行覆盖,只有最后一次写有效,其它变成垃圾数据.
// 索引写入要求按term的升序写入,乱序写入索引结构破坏.
func (this *DiskIndex) WriteIndex(t TermSign, l *InvList) error {
	// 写入索引一次只允许一个在写
	this.lock.Lock()
	defer this.lock.Unlock()

	if this.indexStatus != DiskIndexWriteOnly {
		return errors.New("index status error")
	}

	err := this.writeIndex3(t, l)
	if err != nil {
		return err
	}

	// 索引写入成功才递增termCount
	// 如果写失败,最多占用了index3的文件空间,整个索引还是正常的
	this.currTermCount++
	this.diskStatus.TermCount = this.currTermCount

	// BUG(honggengwei) 每次写都更新状态文件,是否有必要,会不会影响性能
	this.SaveJsonFile()

	return nil
}

// 库中有多少条拉链
func (this *DiskIndex) GetTermCount() int64 {
	return this.diskStatus.TermCount
}

// 打开已存在的磁盘索引
func (this *DiskIndex) Open(path string, name string) error {
	this.lock.Lock()
	defer this.lock.Unlock()

	if this.indexStatus != DiskIndexInit {
		return errors.New("index status error")
	}

	this.filePath = path
	this.fileName = name

	this.StatusFilePath = filepath.Join(this.filePath,
		fmt.Sprintf("%s.index.stat", this.fileName))
	// 磁盘状态文件需要设置的两个步骤:(1)指示要写入的结构;(2)设置写入路径
	this.SelfStatus = &this.diskStatus

	err := this.ParseJsonFile()
	if err != nil {
		return u.ErrFmt("parse file [%s] : %s", this.StatusFilePath, err)
	}

	// 打开三级索引
	this.index3 = new(BigFile)
	ind3name := fmt.Sprintf("%s.index3", this.fileName)
	err = this.index3.Open(this.filePath, ind3name)
	if err != nil {
		return err
	}

	// 打开二级索引
	ind2name := filepath.Join(this.filePath, fmt.Sprintf("%s.index2", this.fileName))
	this.index2, err = os.OpenFile(ind2name, os.O_RDONLY, 0644)
	if err != nil {
		return err
	}

	// 计算一级索引大小
	this.currTermCount = this.diskStatus.TermCount
	index1Sz := this.diskStatus.MaxTermCount * int64(binary.Size(TermSign(0)))

	// 打开一级索引
	this.index1 = new(MmapFile)
	ind1name := fmt.Sprintf("%s.index1", this.fileName)
	err = this.index1.OpenFile(this.filePath, ind1name, uint32(index1Sz))
	if err != nil {
		return u.ErrFmt("mmap open[%s] size[%d] fail : %s", ind1name, index1Sz, err)
	}

	// 构建内存零级索引
	lastBlock := 0
	if this.currTermCount%Index1BolckNum > 0 {
		lastBlock = 1
	}
	this.index0 = make([]TermSign, int(this.currTermCount/Index1BolckNum)+lastBlock)
	var currTerm TermSign
	currTermSize := uint32(binary.Size(currTerm))

	var tmpCount = 0
	for i := int64(0); i < this.currTermCount; i += Index1BolckNum {
		tmp, _ := this.index1.ReadNum(uint32(i)*currTermSize, currTermSize)
		currTerm = TermSign(tmp)
		this.index0[tmpCount] = currTerm
		tmpCount++
	}
	if len(this.index0) != tmpCount {
		return u.ErrFmt("index1[%s] build index0 fail len(index0)[%d] build[%d]",
			ind1name, len(this.index0), tmpCount)
	}

	this.indexStatus = DiskIndexReadOnly
	return nil
}

// 创建全新的磁盘索引,初始化后只允许进行索引写入.
// maxFileSz 索引大文件单个文件的最大大小.
// MaxTermCnt 是预期要写入的term的总数量.
func (this *DiskIndex) Init(path string, name string, maxFileSz uint32, MaxTermCnt int64) error {
	this.lock.Lock()
	defer this.lock.Unlock()

	if this.indexStatus != DiskIndexInit {
		return errors.New("index status error")
	}

	if len(path) == 0 || len(name) == 0 {
		return errors.New("path[%s] name[%s] error")
	}

	this.filePath = path
	this.fileName = name

	this.StatusFilePath = filepath.Join(this.filePath,
		fmt.Sprintf("%s.index.stat", this.fileName))
	// 磁盘状态文件需要设置的两个步骤:(1)指示要写入的结构;(2)设置写入路径
	this.SelfStatus = &this.diskStatus

	this.diskStatus.MaxTermCount = MaxTermCnt

	// 初始化三级索引
	this.index3 = &BigFile{}
	ind3name := fmt.Sprintf("%s.index3", this.fileName)
	err := this.index3.Init(this.filePath, ind3name, maxFileSz)
	if err != nil {
		return err
	}

	// 打开二级索引
	ind2name := filepath.Join(this.filePath, fmt.Sprintf("%s.index2", this.fileName))
	// 打开新文件,创建|截断|只写
	this.index2, err = os.OpenFile(ind2name, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}

	// 计算预期一级索引大小
	index1Sz := this.diskStatus.MaxTermCount * int64(binary.Size(TermSign(0)))

	// 打开一级索引
	this.index1 = new(MmapFile)
	ind1name := fmt.Sprintf("%s.index1", this.fileName)
	err = this.index1.OpenFile(this.filePath, ind1name, uint32(index1Sz))
	if err != nil {
		return u.ErrFmt("mmap open[%s] size[%d] fail : %s", ind1name, index1Sz, err)
	}

	this.indexStatus = DiskIndexWriteOnly

	return this.SaveJsonFile()
}

// 关闭所有索引文件
func (this *DiskIndex) Close() {
	this.lock.Lock()
	defer this.lock.Unlock()

	this.SaveJsonFile()

	this.index0 = nil
	if this.index1 != nil {
		this.index1.Close()
		this.index1 = nil
	}
	if this.index2 != nil {
		this.index2.Close()
		this.index2 = nil
	}
	if this.index3 != nil {
		this.index3.Close()
		this.index3 = nil
	}

	this.indexStatus = DiskIndexClose
}

// DiskIndex构造函数,简单初始化
func NewDiskIndex() *DiskIndex {
	index := DiskIndex{}
	index.indexStatus = DiskIndexInit
	index.diskStatus.MaxTermCount = 0
	index.diskStatus.TermCount = 0
	index.index0 = nil
	index.index1 = nil
	index.index2 = nil
	index.index3 = nil
	index.currTermCount = 0
	return &index
}

// 多个磁盘索引进行merge的时候所采用的最小堆辅助数据结构.只在package内部使用.
type diskIndexMinHeapItem struct {
	// 当前term
	Term TermSign
	// term所在的磁盘索引
	Index *DiskIndex
	// 磁盘索引的迭代器指针
	Iter IndexIterator
}
type diskIndexMinHeap []diskIndexMinHeapItem

// 堆必须支持接口:Len
func (h diskIndexMinHeap) Len() int {
	return len(h)
}

// 堆排序必须支持接口:Less
func (h diskIndexMinHeap) Less(i, j int) bool {
	return h[i].Term < h[j].Term
}

// 堆排序必须支持接口:Swap
func (h diskIndexMinHeap) Swap(i, j int) {
	h[i], h[j] = h[j], h[i]
}

// 堆排序必须支持接口:Push
func (h *diskIndexMinHeap) Push(x interface{}) {
	*h = append(*h, x.(diskIndexMinHeapItem))
}

// 堆排序必须支持接口:Pop
func (h *diskIndexMinHeap) Pop() interface{} {
	old := *h
	n := len(old)
	item := old[n-1]
	*h = old[0 : n-1]
	return item
}
