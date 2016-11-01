package patternmatch

import (
	"fmt"
	"github.com/stretchr/testify/assert"
	"strings"
	"testing"
)

func Test_cutpattern_err1(t *testing.T) {
	tree := newPatternTree()

	mustBe := assert.New(t)

	p1 := "[dfdfddf"
	curPos := 0
	_, err := tree.cutpattern(p1, curPos)
	mustBe.NotNil(err, "error syntax no check")

	p2 := "[]DEF"
	curPos = 0
	_, err = tree.cutpattern(p2, curPos)
	mustBe.NotNil(err, "error syntax no check")

	p3 := "[D#ABC]DEF"
	curPos = 0
	_, err = tree.cutpattern(p3, curPos)
	mustBe.NotNil(err, "error syntax no check")
}

func Test_cutpattern(t *testing.T) {
	tree := newPatternTree()

	mustBe := assert.New(t)

	p1 := "ABC[D:hehe]DEF"
	curPos := 0
	result := make([]string, 0, 0)
	expect := []string{
		"ABC",
		"[D:hehe]",
		"DEF",
	}

	for curPos < len(p1) {
		item, err := tree.cutpattern(p1, curPos)
		mustBe.Nil(err)
		result = append(result, item)
		curPos += len(item)
	}

	mustBe.Equal(len(result), 3, "cut count fail")

	for i := 0; i < len(result); i++ {
		fmt.Println(result[i])
		mustBe.Equal(result[i], expect[i],
			fmt.Sprintf("result[%d] : %s\texpect[%d] : %s", i, result[i], i, expect[i]))
		return
	}
}

func Test_getpatid(t *testing.T) {
	tree := newPatternTree()

	mustBe := assert.New(t)

	w1id, err := tree.getpatid("[W:1-3]")
	mustBe.Nil(err)
	mustBe.True(w1id >= 0 && w1id < MAX_WILDCARD_NUM)

	f1id, err := tree.getpatid("[F:num]")
	mustBe.Nil(err)

	mustBe.True(f1id >= MAX_WILDCARD_NUM && f1id < MAX_WILDCARD_NUM+MAX_FUNC_NUM)

	n1, _ := tree.getpatid("中文")
	n2, _ := tree.getpatid("中文")
	mustBe.Equal(n1, n2)
}

func Test_getpadit_wildcard_limit(t *testing.T) {
	tree := newPatternTree()

	mustBe := assert.New(t)

	for i := 0; i < MAX_WILDCARD_NUM; i++ {
		_, err := tree.getpatid(fmt.Sprintf("[W:1-%d]", 2+i))
		mustBe.Nil(err)
	}

	for i := 0; i < MAX_WILDCARD_NUM; i++ {
		_, err := tree.getpatid(fmt.Sprintf("[W:1-%d]", 2+i))
		mustBe.Nil(err)
	}

	fmt.Println(tree.wildcardItemNum)

	_, err := tree.getpatid("[W:3-4]")
	mustBe.NotNil(err, "exceed max wildcard num,should be fail")
}

func Test_register_wildcard(t *testing.T) {
	tree := newPatternTree()

	mustBe := assert.New(t)

	mustBe.Nil(tree.registerWildcard("[W:3-40]"))

	mustBe.Nil(tree.registerWildcard("[W:3-40]"))

	mustBe.NotNil(tree.registerWildcard("[W:4-3]"))

	mustBe.NotNil(tree.registerWildcard("[W:-4-3]"))
}

func Test_insert(t *testing.T) {
	// TODO
	tree := newPatternTree()
	//mustBe := assert.New(t)

	word_data := newWordTreeData()
	tree.insertOnePattern("ABC[D:name]中文[W:1-3]", "test1", word_data)
	tree.insertOnePattern("ABC[D:name][W:1-3]中文", "test2", word_data)
	tree.insertOnePattern("ABC[D:name][W:1-3]中文ABC", "test3", word_data)
}

func Test_sideflag(t *testing.T) {
	node := newPatTreeNode()
	mustBe := assert.New(t)

	mustBe.False(node.hasFuncSide())
	mustBe.False(node.hasWildcardSide())

	node.withFunc()
	mustBe.True(node.hasFuncSide())
	mustBe.False(node.hasWildcardSide())

	node.withWildcardSide()
	mustBe.True(node.hasFuncSide())
	mustBe.True(node.hasWildcardSide())
}

func Test_pt_case1(t *testing.T) {
	tree := newPatternTree()
	mustBe := assert.New(t)

	ignoreDict := []string{"hehe", "haha", "heihei"}
	ignReader := strings.NewReader(strings.Join(ignoreDict, "\n"))

	patternDict := []string{
		"hehe[D:name]匹配不了\tattr1",
		"lalala[D:name]匹配不了\tattr1",
		"heihei[D:name]匹配不了\tattr1",
		"[D:name]一组固定词\tattr1",
		"[D:name]匹配不了\tattr2"}
	patReader := strings.NewReader(strings.Join(patternDict, "\n"))

	wordDict := []string{"[D:name]", "a", "b"}
	wordReader := strings.NewReader(strings.Join(wordDict, "\n"))

	mustBe.Nil(tree.build(patReader, wordReader, ignReader))

	fmt.Println("------------")

	ctx := newMatchContext("heheb匹配不了")
	res := NewPatMatchResult()
	tree.match(ctx, res)

	// 预期两个模板都能匹配上
	mustBe.Equal(2, len(res.Itemlist))
}

func Test_pt_case2(t *testing.T) {
	tree := newPatternTree()
	mustBe := assert.New(t)

	ignoreDict := []string{"hehe"}
	ignReader := strings.NewReader(strings.Join(ignoreDict, "\n"))

	patternDict := []string{
		"ABC[F:num]DEF[D:name]\tattr1",
		"[D:name]匹配不了\tattr2"}
	patReader := strings.NewReader(strings.Join(patternDict, "\n"))

	wordDict := []string{"[D:name]", "aa", "bb"}
	wordReader := strings.NewReader(strings.Join(wordDict, "\n"))

	mustBe.Nil(tree.build(patReader, wordReader, ignReader))

	fmt.Println("------------")

	ctx := newMatchContext("ABC123456DEFaa")
	res := NewPatMatchResult()
	tree.match(ctx, res)

	// 预期两个模板都能匹配上
	mustBe.Equal(1, len(res.Itemlist))
	item := res.Itemlist[0]
	mustBe.Equal(2, len(item.SlotList))
	mustBe.Equal("[F:num]", item.SlotList[0].Name)
	mustBe.Equal("123456", item.SlotList[0].Value)

	mustBe.Equal("[D:name]", item.SlotList[1].Name)
	mustBe.Equal("aa", item.SlotList[1].Value)
}

func Test_pt_case3(t *testing.T) {
	tree := newPatternTree()
	mustBe := assert.New(t)

	ignoreDict := []string{""}
	ignReader := strings.NewReader(strings.Join(ignoreDict, "\n"))

	patternDict := []string{
		"ABC[W:1-4]DEF[D:name]\tattr1",
		"[D:name]匹配不了\tattr2"}
	patReader := strings.NewReader(strings.Join(patternDict, "\n"))

	wordDict := []string{"[D:name]", "aa", "bb"}
	wordReader := strings.NewReader(strings.Join(wordDict, "\n"))

	mustBe.Nil(tree.build(patReader, wordReader, ignReader))

	fmt.Println("------------")

	ctx := newMatchContext("ABC四个中文DEFaa")
	res := NewPatMatchResult()
	tree.match(ctx, res)

	// 预期两个模板都能匹配上
	mustBe.Equal(1, len(res.Itemlist))
	item := res.Itemlist[0]
	mustBe.Equal(2, len(item.SlotList))
	mustBe.Equal("[W:1-4]", item.SlotList[0].Name)
	mustBe.Equal("四个中文", item.SlotList[0].Value)

	mustBe.Equal("[D:name]", item.SlotList[1].Name)
	mustBe.Equal("aa", item.SlotList[1].Value)

	fmt.Println("------------")

	ctx = newMatchContext("ABC这里超过四个字符DEFaa")
	res = NewPatMatchResult()
	tree.match(ctx, res)
	// 应该一个模板都中不了
	mustBe.Equal(0, len(res.Itemlist))
}
