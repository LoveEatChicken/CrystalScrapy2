package patternmatch

// 匹配输入string,返回可以接受的长度
type matchFuncType func([]rune) int

func matchNumFunc(str []rune) int {
	length := len(str)
	i := 0
	for ; i < length; i++ {
		if str[i] == '.' || str[i]-'0' < 10 {
			continue
		}
		break
	}
	return i
}
