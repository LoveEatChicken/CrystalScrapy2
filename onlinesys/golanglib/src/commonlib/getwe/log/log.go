// log的简单封装
// 我所期待的log接口(我在工作环境熟悉的)是这样的:
// 1. 日志分为多个文件,一个普通INFO日志,一个DEBUG,另外一个是WARN,ERROR,FATAL类型
// 2. INFO一般不采用调用一次打一行日志
// 3. INFO一般一次逻辑处理只打一行
// 4. 除了INFO之外,其它每调用一次,输出一行日志.
package log

import (
	config "commonlib/getwe/config"
	log4go "github.com/alecthomas/log4go"
)

var (
	debugLogger log4go.Logger
	infoLogger  log4go.Logger
	errorLogger log4go.Logger
)

func init() {
	debugLogger = make(log4go.Logger)
	infoLogger = make(log4go.Logger)
	errorLogger = make(log4go.Logger)
}

func newFileFilter(file string, rotateDaily bool) *log4go.FileLogWriter {
	flw := log4go.NewFileLogWriter(file, false)
	//flw.SetFormat("[%D %T] [%L] (%S) %M")
	flw.SetFormat("[%D %T] [%L] %M")
	flw.SetRotateLines(0)
	flw.SetRotateSize(0)
	flw.SetRotateDaily(false)

	return flw
}

func LoadConfiguration(confPath string) error {

	conf, err := config.NewConf(confPath)
	if err != nil {
		return err
	}

	var filt *log4go.FileLogWriter

	// debug
	debugEnable := conf.Bool("debug.Enable")
	debugFile := conf.String("debug.FileName")
	debugRotateDaily := conf.BoolDefault("debug.RotateDaily", true)
	filt = nil
	if debugEnable {
		filt = newFileFilter(debugFile, debugRotateDaily)
	}
	debugLogger["debug"] = &log4go.Filter{log4go.DEBUG, filt}

	// info
	infoEnable := conf.Bool("info.Enable")
	infoFile := conf.String("info.FileName")
	infoRotateDaily := conf.BoolDefault("info.RotateDaily", true)
	filt = nil
	if infoEnable {
		filt = newFileFilter(infoFile, infoRotateDaily)
	}
	infoLogger["info"] = &log4go.Filter{log4go.INFO, filt}

	// error
	errorEnable := conf.Bool("error.Enable")
	errorFile := conf.String("error.FileName")
	errorRotateDaily := conf.BoolDefault("error.RotateDaily", true)
	filt = nil
	if errorEnable {
		filt = newFileFilter(errorFile, errorRotateDaily)
	}
	errorLogger["error"] = &log4go.Filter{log4go.WARNING, filt}

	return nil
}
