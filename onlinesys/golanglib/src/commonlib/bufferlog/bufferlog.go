// 实现一般打日志的接口，但是实际上不打只是把日志信息缓存起来
// 最后集中返回
package bufferlog

import (
	"fmt"
	"strings"
)

type BufferLogger struct {
	sep    string // 最终输出时使用的分隔符
	logstr []string
}

func NewBufferLogger() *BufferLogger {
	bl := new(BufferLogger)
	bl.sep = " "
	bl.logstr = make([]string, 0)
	return bl
}

func (this *BufferLogger) SetSep(s string) {
	this.sep = s
}

// Info日志先存起来,调用GetAllInfo的时候输出日志
// 支持日常用法
// Info(object,xxx) : 输出一个对象的字符串化表示,忽略后面的参数
// Info(string) : 直接输出
// Info(strA,strB) : 输出strA:strB
// Info(strA,object) : 输出strA : object.string()
func (this *BufferLogger) Info(arg ...interface{}) error {

	var result string

	if len(arg) <= 1 {
		result = fmt.Sprintf("%s", arg)
	} else if len(arg) == 2 {
		result = fmt.Sprint(arg[0]) + ":" + fmt.Sprint(arg[1])
	} else {
		result = fmt.Sprint(arg[0]) + ":" + fmt.Sprint(arg[1:])
	}

	this.logstr = append(this.logstr, result)
	return nil
}

// 输出全部Info日志
func (this *BufferLogger) GetAllInfo() string {
	res := strings.Join(this.logstr, this.sep)
	this.logstr = this.logstr[:0]
	return res
}
