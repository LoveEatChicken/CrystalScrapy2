package patternmatch

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

func Test_num(t *testing.T) {
	assert := assert.New(t)

	assert.Equal(0, matchNumFunc([]rune("abc123")))
	assert.Equal(1, matchNumFunc([]rune("1abc")))
	assert.Equal(3, matchNumFunc([]rune("1.3abc")))

}
