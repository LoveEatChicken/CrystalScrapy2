package patternmatch

import (
	"bufio"
	log "commonlib/beegologs"
	"errors"
	"fmt"
	"io"
	"regexp"
	"strconv"
	"strings"
)

const (
	MAX_FUNC_NUM           = 20   // 支持最多的函数个数
	MAX_WILDCARD_NUM       = 20   // 支持最多的通配符个数
	MAX_SEARCH_STATE_COUNT = 1000 // 最多递归检索状态数
	MAX_RESULT_COUNT       = 32   // 最多结果数
)

const (
	INVALID_DATA = -1
	IGNORE_PATID = -2 // 省略词的模板id是一个特殊id
)

const (
	SIDE_HAVE_FUNC     = 1 << 0 // 边有函数
	SIDE_HAVE_WILDCARD = 1 << 1 // 边有通配符
)

// 匹配上下文
// 递归match中记录状态
type matchContext struct {
	query     []rune // 输入的query
	currPos   int    // 当前状态匹配到的位置
	currState int    // 当前在状态树中匹配到的节点

	patIdList []int // 一路匹配下来匹配的patId列表缓冲区
	patIdPos  []int // 第i个匹配到的patId在原query中的起始位置
	patIdLen  []int // 第i个匹配到的patId的query段长度
	patIdNum  int   // 以上三个数组的实际有效数据个数

	searchCount    int // 递归搜索了多少次
	maxSearchCount int // 最多搜索次数

	maxResultCount int // 最多结果数，结果够了也提前退出

	depth int // 递归深度，调试用

	cache map[string]int
}

func newMatchContext(query string) *matchContext {
	ctx := new(matchContext)
	ctx.query = []rune(query)
	ctx.currPos = 0
	ctx.searchCount = 0
	ctx.maxSearchCount = MAX_SEARCH_STATE_COUNT
	ctx.maxResultCount = MAX_RESULT_COUNT

	ctx.patIdList = make([]int, len(ctx.query)) //分配query的长度，按rune算不会更长
	ctx.patIdPos = make([]int, len(ctx.query))
	ctx.patIdLen = make([]int, len(ctx.query))
	ctx.patIdNum = 0

	ctx.depth = 0
	ctx.cache = make(map[string]int)
	return ctx
}

// 整个递归搜索过程对结果有影响就是ctx.currState, ctx.currPos
func (ctx *matchContext) getCacheKey() string {
	return fmt.Sprintf("state_%d_pos_%d", ctx.currState, ctx.currPos)
}

// 整个递归过程影响结果的参数组成cache key
// 一样则提前退出
func (ctx *matchContext) isInCache() bool {
	key := ctx.getCacheKey()
	_, ok := ctx.cache[key]
	if !ok {
		return false
	}
	return true
}

func (ctx *matchContext) setCache() {
	key := ctx.getCacheKey()
	ctx.cache[key] = 1
}

// 模板节点
type patternItem struct {
	// 模板原文,比如：[D:ABC]、[W:1-3]、固定词、
	text string
	// 附加属性
	// attr string
	// 简化，不需要用到
}

func (item *patternItem) isWildCard() bool {
	if len(item.text) <= 4 {
		return false
	}

	if item.text[:3] == "[W:" {
		return true
	}
	return false
}

func (item *patternItem) isFunc() bool {
	if len(item.text) <= 4 {
		return false
	}

	if item.text[:3] == "[F:" {
		return true
	}
	return false
}

func (item *patternItem) isSlot() bool {
	if len(item.text) <= 4 {
		return false
	}

	if item.text[:3] == "[D:" {
		return true
	}
	return false
}

// 是否是普通词  ABC[D:name]中的ABC就是普通词
func (item *patternItem) isNormal() bool {
	// 长度不够，肯定是固定词
	if len(item.text) < 2 {
		return true
	}

	t := item.text[1]

	return t != 'W' && t != 'F' && t != 'D'
}

func newPatternItem(text string) *patternItem {
	item := new(patternItem)
	item.text = text
	return item
}

// 模板树状态节点
type patTreeNode struct {
	// 状态节点的属性
	// 叶子状态节点则有值
	// 叶子存储到达该节点的模板原文和模板属性
	Pattern

	/*
		// 边指针
		// 模板树的边关系由patTreeSide维护，指向边数据段的起始位置和长度
		sidePos int
		sideLen int
	*/

	// 该状态下的所有的边 key/value
	// 当前状态遇到key(patId)时应该转移到value(nextState)
	side map[int]int

	// 边特殊标记
	// SIDE_HAVE_FUNC ...
	sideFlag int
}

func newPatTreeNode() *patTreeNode {
	n := new(patTreeNode)
	n.PatternText = ""
	n.PatternText = ""
	n.side = make(map[int]int, 0)
	n.sideFlag = 0
	return n
}

func (n *patTreeNode) withWildcardSide() {
	n.sideFlag |= SIDE_HAVE_WILDCARD
}

func (n *patTreeNode) withFunc() {
	n.sideFlag |= SIDE_HAVE_FUNC
}

func (n *patTreeNode) hasWildcardSide() bool {
	return n.sideFlag&SIDE_HAVE_WILDCARD == SIDE_HAVE_WILDCARD
}

func (n *patTreeNode) hasFuncSide() bool {
	return n.sideFlag&SIDE_HAVE_FUNC == SIDE_HAVE_FUNC
}

// 当前状态插入新的边
// 如果patId能找到旧的边则复用，否则新的状态点就是nextState
// 返回新的状态点下标
func (n *patTreeNode) addSide(patId int, nextState int) (int, error) {
	oldState, ok := n.side[patId]
	if !ok {
		n.side[patId] = nextState
		return nextState, nil
	}
	// 如果找得到则复用这条边
	return oldState, nil
}

// 当前状态匹配patId时转移到的下一个状态,搜索过程中使用
func (n *patTreeNode) matchNextState(patId int) (int, error) {
	next, ok := n.side[patId]
	if !ok {
		return INVALID_DATA, errors.New("not found next state")
	}
	return next, nil
}

func (n *patTreeNode) setPattern(patText, patAttr string) error {
	n.PatternText = patText
	n.PatternAttr = patAttr
	return nil
}

// 是否是叶子节点
// 表示有模板到此结束
func (n *patTreeNode) hasPattern() bool {
	return n.PatternText != ""
}

/*
// 模板树的边关系
// patNodeList[parent]状态在匹配到patId成分后
// 可转移到patNodeList[child]状态
type patTreeSide struct {
	// 上一个状态节点
	parent int

	// 模板id
	// 这个边关系表明上一个状态输入patId
	patId int

	// 下一个状态节点
	child int
}

func newPatTreeSide() patTreeSide {
	s := patTreeSide{}
	s.parent = INVALID_DATA
	s.patId = INVALID_DATA
	s.child = INVALID_DATA
	return s
}
*/

// 通配符节点信息
type wildcardNode struct {
	// 通配符名称
	name string
	// 通配符前后闭空间长度:[down,up]
	up   int
	down int
}

type funcNode struct {
	// 函数节点名称
	name string

	// 回调函数
	Func matchFuncType
}

type patternTree struct {
	// 所有模板成分组成的数组
	// patItemList[patid]的下标patid的含义就是该模板成分所分配的id
	patItemList     []*patternItem
	wildcardItemNum int // patItemList里面通配符的数量
	funcItemNum     int // patItemList里面函数的数量

	// 模板树的节点
	patNodeList []*patTreeNode

	// 模板树的边关系
	//patSideList []patTreeSide

	// 通配符数组
	wildcardNodeHash map[string]wildcardNode

	// 预定义函数hash
	funcNodeHash map[string]funcNode

	// 词典树
	wTree *wordTree
}

// 检查输入的state状态是否有效
// 有效可用则直接返回状态id
// 无效则为模板树分配一个新的状态，返回新的状态id
func (tree *patternTree) checkAllocState(currState int) int {
	// 有效
	if currState < len(tree.patNodeList) {
		return currState
	}

	// currStata还不能写入数据分配一个新的state
	tree.patNodeList = append(tree.patNodeList, newPatTreeNode())
	return len(tree.patNodeList) - 1
}

func (tree *patternTree) insertWord(r io.Reader, word_data wordTreeData) error {
	var err error
	scanner := bufio.NewScanner(r)

	patId := INVALID_DATA

	for scanner.Scan() {
		line := scanner.Text()
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "#") {
			continue
		}
		arr := strings.Split(line, "\t")
		item := newPatternItem(arr[0]) // 暂时不支持单词附加属性

		if item.isSlot() {
			patId, err = tree.getpatid(item.text)
			if err != nil {
				return err
			}
		} else {
			if patId == INVALID_DATA {
				return errors.New("word dict syntax error")
			}
			word_data.insert(arr[0], patId, "")
		}
	}
	return nil
}

func (tree *patternTree) insertIgnore(r io.Reader, word_data wordTreeData) error {
	scanner := bufio.NewScanner(r)

	for scanner.Scan() {
		line := scanner.Text()
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "#") {
			continue
		}
		arr := strings.Split(line, "\t")
		word_data.insert(arr[0], IGNORE_PATID, "")
	}
	return nil
}

// 输入一个模板进行解析更新模板树状态
func (tree *patternTree) insertPattern(r io.Reader, word_data wordTreeData) error {
	var err error
	scanner := bufio.NewScanner(r)

	for scanner.Scan() {
		line := scanner.Text()
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "#") {
			continue
		}
		arr := strings.Split(line, "\t")
		if len(arr) == 1 {
			arr = append(arr, "") // 没有模板属性
		}
		err = tree.insertOnePattern(arr[0], arr[1], word_data)
		if err != nil {
			return err
		}
	}
	return nil
}

func (tree *patternTree) insertOnePattern(pattern string, attr string, word_data wordTreeData) error {

	currPos := 0

	currState := 0 // 当前状态，在tree.patNodeList中的下标
	nextState := 0 // 下一个状态

	for currPos < len(pattern) {
		text, err := tree.cutpattern(pattern, currPos)
		if err != nil {
			return err
		}

		item := newPatternItem(text)

		if item.isWildCard() {
			err := tree.registerWildcard(item.text)
			if err != nil {
				return err
			}
		}

		patId, err := tree.getpatid(item.text)
		if err != nil {
			return err
		}

		if item.isNormal() {
			// 后面会统一用这个word_data构建普通词trie树
			word_data.insert(item.text, patId, "")
		}

		// 保证currState可以写入状态了
		currState = tree.checkAllocState(currState)
		// 如果需要开辟新的状态，则下一个状态是nextState
		nextState = len(tree.patNodeList)

		// 当前状态插入新的边
		nextState, err = tree.patNodeList[currState].addSide(patId, nextState)
		if err != nil {
			return err
		}

		// 记录该状态是否有特殊边：函数或者通配符
		if item.isFunc() {
			tree.patNodeList[currState].withFunc()
		}
		if item.isWildCard() {
			tree.patNodeList[currState].withWildcardSide()
		}

		log.Llog.Debug("currState:%d\titem:%s\tpatId:%d\tnextState:%d", currState, item.text, patId, nextState)
		// 开始处理下一轮状态
		currState = nextState
		currPos += len(item.text)
	}

	// 在最后一个状态点保存模板的属性信息
	currState = tree.checkAllocState(currState)
	tree.patNodeList[currState].setPattern(pattern, attr)

	log.Llog.Debug("currState:%d\tpattern:%s\tattr:%s", currState, pattern, attr)
	return nil
}

func (tree *patternTree) cutpattern(pattern string, currPos int) (string, error) {
	// 找到模板成分[X:xxxx]
	begin := strings.Index(pattern[currPos:], "[")
	// 不存在[
	if begin == -1 {
		return pattern[currPos:], nil
	}
	// [  之前有内容可以直接返回
	if begin > 0 {
		return pattern[currPos : currPos+begin], nil
	}

	end := strings.Index(pattern[currPos:], "]")
	// 找不到匹配的]
	if end == -1 {
		return "", errors.New("syntax error : [ and ] not match")
	}

	if end < begin {
		return "", errors.New("syntax error : ] comes before [")
	}

	item := pattern[currPos+begin : currPos+end+1]
	if len(item) < 3 {
		return "", errors.New("syntax error : [] without type")
	}
	if string(item[2]) != ":" {
		return "", errors.New("syntax error : [] without :")
	}

	return item, nil
}

func (tree *patternTree) getpatid(text string) (int, error) {
	begin := 0
	end := 0

	item := newPatternItem(text)

	if item.isWildCard() {
		begin = 0
		end = tree.wildcardItemNum
	} else if item.isFunc() {
		begin = MAX_WILDCARD_NUM
		end = begin + tree.funcItemNum
	} else {
		begin = MAX_WILDCARD_NUM + MAX_FUNC_NUM
		end = len(tree.patItemList)
	}

	// 检查是否分配过
	for i := begin; i < end; i++ {
		if tree.patItemList[i].text == text {
			return i, nil
		}
	}

	// 需要进行分配
	// 通配符和函数都是预分配好的空间，直接写入
	if item.isWildCard() {
		if tree.wildcardItemNum >= MAX_WILDCARD_NUM {
			return INVALID_DATA, errors.New("exceed max wildcard num")
		}
		tree.patItemList[end] = item
		tree.wildcardItemNum++
		return end, nil
	}
	if item.isFunc() {
		if tree.funcItemNum >= MAX_FUNC_NUM {
			return INVALID_DATA, errors.New("exceed max func num")
		}
		tree.patItemList[end] = item
		tree.funcItemNum++
		return end, nil
	}
	// 固定词和模板成分在末尾添加，完成patId分配
	tree.patItemList = append(tree.patItemList, item)

	// 下标才是patId，需要减1
	return len(tree.patItemList) - 1, nil
}

func (tree *patternTree) registerFunc(name string, f matchFuncType) error {
	_, ok := tree.funcNodeHash[name]
	if ok {
		return nil
	}

	tree.funcNodeHash[name] = funcNode{name: name, Func: f}

	return nil
}

func (tree *patternTree) getFunc(name string) matchFuncType {
	f, ok := tree.funcNodeHash[name]
	if ok {
		return f.Func
	}
	return nil
}

func (tree *patternTree) registerWildcard(name string) error {

	rex := regexp.MustCompile(`\[W:(\d+)-(\d+)\]`)
	group := rex.FindStringSubmatch(name)
	if group == nil {
		return errors.New(fmt.Sprintf("regex fail %s is not valid wildcard", name))
	}

	n := wildcardNode{}
	n.name = name
	n.down, _ = strconv.Atoi(group[1])
	n.up, _ = strconv.Atoi(group[2])

	if n.down < 0 || n.up < 0 || n.down > n.up {
		return errors.New(fmt.Sprintf("%s is not valid wildcard", name))
	}

	_, ok := tree.wildcardNodeHash[name]
	if ok {
		return nil
	}

	tree.wildcardNodeHash[name] = n

	return nil
}

func (tree *patternTree) getWildcard(name string) *wildcardNode {
	n, ok := tree.wildcardNodeHash[name]
	if ok {
		return &n
	}
	return nil
}

func (tree *patternTree) build(pat, word, ignore io.Reader) error {
	word_data := newWordTreeData()

	err := tree.insertWord(word, word_data)
	if err != nil {
		return err
	}

	err = tree.insertPattern(pat, word_data)
	if err != nil {
		return err
	}

	err = tree.insertIgnore(ignore, word_data)
	if err != nil {
		return err
	}

	err = tree.wTree.insert(word_data)
	if err != nil {
		return err
	}

	tree.registerFunc("[F:num]", matchNumFunc)

	word_data = nil

	return nil
}

// 递归搜索，能够走完匹配状态的把结果写入res
func (tree *patternTree) match(ctx *matchContext, res *PatMatchResult) {
	if ctx.isInCache() {
		return
	}
	ctx.setCache()

	ctx.searchCount++
	ctx.depth++
	defer func() {
		log.Llog.Debug("leave depth\t:\t%d", ctx.depth)
		ctx.depth--
	}()
	log.Llog.Debug("into depth\t:\t%d", ctx.depth)
	log.Llog.Debug("search count{%d}", ctx.searchCount)

	log.Llog.Warn("currState[%d] currPos[%d]", ctx.currState, ctx.currPos)

	// 搜索状态太久了，提前退出
	if ctx.searchCount > ctx.maxSearchCount {
		log.Llog.Debug("searchCount {%d} > maxSearchCount{%d}", ctx.searchCount, ctx.maxSearchCount)
		return
	}
	// 到达末尾了
	if ctx.currPos > len(ctx.query) {
		log.Llog.Debug("curPos{%d} > query len {%d}", ctx.currPos, len(ctx.query))
		return
	}
	// 结果足够多
	if len(res.Itemlist) >= ctx.maxResultCount {
		log.Llog.Debug("result enough")
		return
	}

	// 状态超出最大范围
	// TODO 什么样的情况会走到这样的case
	if ctx.currState >= len(tree.patNodeList) {
		log.Llog.Debug("currState{%d} > len(tree.patNodeList) {%d}", ctx.currState,
			len(tree.patNodeList))
		return
	}

	currNode := tree.patNodeList[ctx.currState] // 当前走到的状态点
	log.Llog.Debug("currPos[%d],len(query)[%d] currState[%d] hasPattern[%t]",
		ctx.currPos, len(ctx.query), ctx.currState, currNode.hasPattern())
	// 匹配完query,同时走到一个状态点带有叶子节点信息
	if ctx.currPos == len(ctx.query) && currNode.hasPattern() {
		resItem := NewPatMatchItem()
		resItem.PatternText = currNode.PatternText
		resItem.PatternAttr = currNode.PatternAttr
		log.Llog.Info("query match pat {%s} attr{%s}", resItem.PatternText,
			resItem.PatternAttr)

		for i := 0; i < ctx.patIdNum; i++ {
			patId := ctx.patIdList[i]
			// 可省词匹配,不返回槽位信息
			if patId == IGNORE_PATID {
				continue
			}

			patItem := tree.patItemList[patId]
			// 固定词也不返回
			if patItem.isNormal() {
				continue
			} else {
				pos := ctx.patIdPos[i]
				len := ctx.patIdLen[i]

				resItem.SlotList = append(resItem.SlotList, Slot{
					Name:  patItem.text,
					Value: string(ctx.query[pos : pos+len]),
				})
			}
		}
		log.Llog.Debug("%v", resItem.SlotList)
		// 新的一条模板识别结果
		res.Itemlist = append(res.Itemlist, resItem)
		// 完全匹配，query都遍历完了可以返回了
		return
	}

	// query还没匹配完，开始匹配不同的成分
	tree.matchFunc(ctx, res)
	tree.matchWildCard(ctx, res)
	tree.matchItem(ctx, res)
}

func (tree *patternTree) matchFunc(ctx *matchContext, res *PatMatchResult) {
	currNode := tree.patNodeList[ctx.currState]

	// 当前状态没有函数边
	if currNode.hasFuncSide() == false {
		return
	}

	word := []rune(ctx.query[ctx.currPos:])

	// 遍历所有边
	for patId, nextState := range currNode.side {
		patItem := tree.patItemList[patId]
		if patItem.isFunc() == false {
			continue
		}

		function := tree.getFunc(patItem.text)
		if function == nil {
			log.Llog.Warn("func [%s] not found", patItem.text)
			continue
		}

		fLen := function(word)

		ctx.patIdList[ctx.patIdNum] = patId
		ctx.patIdPos[ctx.patIdNum] = ctx.currPos
		ctx.patIdLen[ctx.patIdNum] = fLen
		ctx.patIdNum++
		log.Llog.Debug("match func item{%s}, nextState{%d} try {%s}",
			string(ctx.query[ctx.currPos:ctx.currPos+fLen]),
			nextState,
			string(ctx.query[ctx.currPos+fLen:]))

		tmpCurrState := ctx.currState

		ctx.currPos += fLen
		ctx.currState = nextState
		tree.match(ctx, res)

		ctx.patIdNum--
		ctx.currPos -= fLen
		ctx.currState = tmpCurrState
	}
}

func (tree *patternTree) matchWildCard(ctx *matchContext, res *PatMatchResult) {
	currNode := tree.patNodeList[ctx.currState]

	if currNode.hasWildcardSide() == false {
		return
	}

	// 遍历所有边
	for patId, nextState := range currNode.side {
		patItem := tree.patItemList[patId]
		if patItem.isWildCard() == false {
			continue
		}

		wcNode := tree.getWildcard(patItem.text)
		if wcNode == nil {
			log.Llog.Warn("wildNode [%s] not found", patItem.text)
			continue
		}

		for i := wcNode.down; i <= wcNode.up; i++ {
			if ctx.currPos+i > len(ctx.query) {
				break
			}

			ctx.patIdList[ctx.patIdNum] = patId
			ctx.patIdPos[ctx.patIdNum] = ctx.currPos
			ctx.patIdLen[ctx.patIdNum] = i
			ctx.patIdNum++
			log.Llog.Debug("match wildcard item{%s}, nextState{%d} try {%s}",
				string(ctx.query[ctx.currPos:ctx.currPos+i]),
				nextState,
				string(ctx.query[ctx.currPos+i:]))

			tmpCurrState := ctx.currState

			ctx.currPos += i
			ctx.currState = nextState
			tree.match(ctx, res)

			ctx.patIdNum--
			ctx.currPos -= i
			ctx.currState = tmpCurrState
		}
	}
}

func (tree *patternTree) matchItem(ctx *matchContext, res *PatMatchResult) {

	word := []rune(ctx.query[ctx.currPos:])
	log.Llog.Debug("pattern try match word {%s}", string(word))
	wtRes, err := tree.wTree.search(word)
	if err != nil {
		// TODO any warninng?
		log.Llog.Debug(err.Error())
		return
	}

	for _, r := range wtRes {
		log.Llog.Debug("patId{%d}, len{%d}", r.patId, r.prefixLen)
		// 可省词
		if r.patId == IGNORE_PATID {
			// 记录可省词的一个匹配结果
			ctx.patIdList[ctx.patIdNum] = IGNORE_PATID
			ctx.patIdPos[ctx.patIdNum] = ctx.currPos
			ctx.patIdLen[ctx.patIdNum] = r.prefixLen
			ctx.patIdNum++
			log.Llog.Debug("currState{%d} match ignore item{%s}, nextState{%d} try{%s}",
				ctx.currState,
				string(ctx.query[ctx.currPos:ctx.currPos+r.prefixLen]),
				ctx.currState, // 可省词匹配，状态不变
				string(ctx.query[ctx.currPos+r.prefixLen:]))

			ctx.currPos += r.prefixLen // query前进
			tree.match(ctx, res)       // 先假设可省词都忽略，然后进行递归

			ctx.patIdNum-- // 可省词不忽略，进行其它匹配
			ctx.currPos -= r.prefixLen
		} else {
			// 模板词和固定词
			currNode := tree.patNodeList[ctx.currState]
			nextState, err := currNode.matchNextState(r.patId)
			if err != nil {
				log.Llog.Debug("currState{%d},patId{%d} matchNext State fail",
					ctx.currState, r.patId)
			} else {
				ctx.patIdList[ctx.patIdNum] = r.patId
				ctx.patIdPos[ctx.patIdNum] = ctx.currPos
				ctx.patIdLen[ctx.patIdNum] = r.prefixLen
				ctx.patIdNum++
				log.Llog.Debug("match name item{%s}, nextState{%d} try {%s}",
					string(ctx.query[ctx.currPos:ctx.currPos+r.prefixLen]),
					nextState,
					string(ctx.query[ctx.currPos+r.prefixLen:]))

				tmpCurrState := ctx.currState

				ctx.currPos += r.prefixLen
				ctx.currState = nextState
				tree.match(ctx, res)

				ctx.patIdNum--
				ctx.currPos -= r.prefixLen
				ctx.currState = tmpCurrState
			}
		}
	}

}

func newPatternTree() *patternTree {
	ft := &patternTree{}

	ft.patItemList = make([]*patternItem, MAX_FUNC_NUM+MAX_WILDCARD_NUM, 1024) //预留
	ft.wildcardItemNum = 0
	ft.funcItemNum = 0

	ft.patNodeList = make([]*patTreeNode, 0)
	//ft.patSideList = make([]patTreeSide, 0)

	ft.wildcardNodeHash = make(map[string]wildcardNode)
	ft.funcNodeHash = make(map[string]funcNode)

	ft.wTree = newWordTree()

	return ft
}
