package patternmatch

import (
	"fmt"
	"github.com/stretchr/testify/assert"
	"log"
	"testing"
)

func Test_wordtree_case1(t *testing.T) {
	mustBe := assert.New(t)

	wt := newWordTree()
	word_data := newWordTreeData()
	word_data.insert("hehe", IGNORE_PATID, "")
	word_data.insert("heh", IGNORE_PATID, "")
	word_data.insert("he", IGNORE_PATID, "")
	word_data.insert("h", IGNORE_PATID, "")
	word_data.insert("1h", IGNORE_PATID, "")
	word_data.insert("haha", IGNORE_PATID, "")
	word_data.insert("heihei", IGNORE_PATID, "")
	word_data.insert("中文1", 1, "attr1")
	word_data.insert("中文2", 2, "attr2")
	word_data.insert("中文3", 3, "attr3")
	word_data.insert("中文4", 4, "attr4")

	mustBe.Nil(wt.insert(word_data))

	word := []rune("hehe")

	res, err := wt.search(word)
	mustBe.Nil(err)
	mustBe.Equal(len(res), 4)
	for _, r := range res {
		log.Printf("match word {%s} patId{%d}\n", string(word[:r.prefixLen]), r.patId)
		mustBe.Equal(IGNORE_PATID, r.patId)
	}

	word = []rune("中文123")
	res, err = wt.search(word)
	mustBe.Nil(err)
	mustBe.Equal(1, len(res))
	mustBe.Equal(1, res[0].patId)
	mustBe.Equal("attr1", res[0].attr)

}

func Test_case2(t *testing.T) {
	mustBe := assert.New(t)

	wt := newWordTree()
	word_data := newWordTreeData()
	word_data.insert("hehe", 1, "attr1")
	word_data.insert("hehe", 2, "attr2")
	word_data.insert("hehe", 3, "attr3")

	mustBe.Nil(wt.insert(word_data))

	word := []rune("hehe")

	res, err := wt.search(word)
	mustBe.Nil(err)
	mustBe.Equal(len(res), 3)
	for _, r := range res {
		log.Printf("match word {%s} patId{%d} attr{%s}\n",
			string(word[:r.prefixLen]), r.patId, r.attr)
		mustBe.Equal(fmt.Sprintf("attr%d", r.patId), r.attr)
	}
}
