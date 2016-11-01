package beegologs

import (
	"strconv"

	logs "commonlib/logs"
	"commonlib/simplejson"
	"fmt"
)

var (
	// 文件logger
	Llog *logs.BeeLogger
)

func init() {
	// 本地默认初始化一个consolelogger
	InitConsoleLogger("100", "7")
}

// 外部初始化logger后设置进来
func SetFileLogger(l *logs.BeeLogger) {
	Llog = l
}

func InitConsoleLogger(maxChannelSize string, level string) error {
	isize, _ := strconv.Atoi(maxChannelSize)
	ilevel, _ := strconv.Atoi(level)
	Llog = logs.NewLogger(int64(isize))
	Llog.EnableFuncCallDepth(true)
	jlog := simplejson.New()
	jlog.Set("level", ilevel)
	strBuf, err := jlog.MarshalJSON()
	if err != nil {
		fmt.Println(err.Error())
		return err
	}
	err = Llog.SetLogger("console", string(strBuf))
	if err != nil {
		fmt.Println(err.Error())
		return err
	}
	return nil
}

// 外部通过参数设置一个文件logger
func InitFileLogger(maxChannelSize string, fileName string, level string) error {
	isize, _ := strconv.Atoi(maxChannelSize)
	ilevel, _ := strconv.Atoi(level)

	Llog = logs.NewLogger(int64(isize))
	Llog.EnableFuncCallDepth(true)
	jlog := simplejson.New()
	jlog.Set("filename", fileName)
	jlog.Set("daily", true)
	jlog.Set("maxdays", 100000)
	jlog.Set("level", ilevel)
	strBuf, err := jlog.MarshalJSON()
	if err != nil {
		return err
	}
	Llog.SetLogger("file", string(strBuf))
	return nil
}
