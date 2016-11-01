package main

import (
	"commonlib/getwe/config"
	"commonlib/logs"
	"commonlib/simplejson"
	"fmt"
	pb "gorpcimp/bot"
	"net"
	"net/http"
	"os"
	"strconv"
	"time"

	"golang.org/x/net/context"
)

type ChatSvr struct {
	confFile string      //保存配置文件路径,便于重新加载配置
	conf     config.Conf //配置句柄,从中获取配置数据

	//log句柄 : 系统日志 & 远程业务日志
	Llog *logs.BeeLogger //系统日志：本地文件

	//http 服务器
	bindAddr     string
	readTimeout  int
	writeTimeout int

	//业务数据部分
	botname   string //机器人名称
	lisHandle net.Listener

	//图灵机器人配置
	TLApiKey     string
	TLApiUrl     string
	TLHttpClient *http.Client //http client

	//进程ID
	PID        int
	SeqNum     int64 //请求序列号
	ProcSuffix int   //服务器下标
}

/**
 *  初始化服务器
 *      @param confFile 配置文件 ini
 *
 *
 */
func (ds *ChatSvr) Init() error {
	ds.PID = os.Getpid()
	ds.SeqNum = 0

	var err error = nil
	//解析配置文件
	ds.conf, err = config.NewConf(ds.confFile)
	if err != nil {
		return err
	}

	//初始化日志
	err = ds.initlog()
	if err != nil {
		return err
	}

	//初始化图灵机器人
	err = ds.init_tuling()
	if err != nil {
		return err
	}
	ds.Llog.Info("--------------------- Service initial -------------------------")

	//初始化服务器
	ds.Llog.Info("------ Init Task ------")
	ds.bindAddr = ds.conf.StringDefault("task.bind_addr", "127.0.0.1:10030")
	ds.readTimeout, _ = strconv.Atoi(ds.conf.StringDefault("task.read_timeout", "10"))
	ds.writeTimeout, _ = strconv.Atoi(ds.conf.StringDefault("task.write_timeout", "10"))
	ds.botname = ds.conf.StringDefault("task.bot_name", "chat_service")
	ds.Llog.Info("bind : %s", ds.bindAddr)
	ds.Llog.Info("ReadTimeOut : %d", ds.readTimeout)
	ds.Llog.Info("WriteTimeOut : %d", ds.writeTimeout)
	ds.Llog.Info("BotName : %s", ds.botname)

	ds.lisHandle, err = net.Listen("tcp", ds.bindAddr)
	if err != nil {
		return err
	}

	//初始化业务数据
	ds.ProcSuffix, _ = strconv.Atoi(ds.conf.StringDefault("task.svr_suffix", "10000"))
	ds.Llog.Info("--------------------- Service running -------------------------")
	return nil

}

//启动服务器
func (ds *ChatSvr) ListenHandle() *net.Listener {
	return &ds.lisHandle
}

//初始化日志服务
func (ds *ChatSvr) initlog() error {
	local_log_channel, _ := strconv.Atoi(ds.conf.StringDefault("log.locallog.max_channel_size", "100"))
	llog_name := ds.conf.StringDefault("log.locallog.filename", "./charsvr.log")
	llog_level, _ := strconv.Atoi(ds.conf.StringDefault("log.locallog.level", "6"))
	ds.Llog = logs.NewLogger(int64(local_log_channel))
	ds.Llog.EnableFuncCallDepth(true)
	jlog := simplejson.New()
	jlog.Set("filename", llog_name)
	jlog.Set("daily", true)
	jlog.Set("maxdays", 100000)
	jlog.Set("level", llog_level)
	str_buf, err := jlog.MarshalJSON()
	if err != nil {
		return err
	}
	ds.Llog.SetLogger("file", string(str_buf))
	ds.Llog.Info("LocalLogConfig as follow : %s", string(str_buf))

	return nil
}

//初始化图灵机器人介入
func (ds *ChatSvr) init_tuling() error {
	conn_timeout, _ := strconv.Atoi(ds.conf.StringDefault("tuling.connect_timeout", "10"))
	send_timeout, _ := strconv.Atoi(ds.conf.StringDefault("tuling.send_timeout", "5"))
	ds.TLApiKey = ds.conf.StringDefault("tuling.apikey", "")
	if ds.TLApiKey == "" {
		return fmt.Errorf("need config item : tuling.apikey")
	}
	ds.TLApiUrl = ds.conf.StringDefault("tuling.apiurl", "http://www.tuling123.com/openapi/api")

	//定义http client
	tr := &http.Transport{
		Dial: func(netw, addr string) (net.Conn, error) {
			c, err := net.DialTimeout(netw, addr, time.Second*time.Duration(conn_timeout))
			if err != nil {
				return nil, err
			}
			return c, nil
		},
		MaxIdleConnsPerHost:   100,                                       //每个host最大空闲连接
		ResponseHeaderTimeout: time.Second * time.Duration(send_timeout), //数据收发5秒超时
	}
	ds.TLHttpClient = &http.Client{Transport: tr}
	return nil
}

/**
 *	grpc 依据proto，必须实现Work方法,implement BotServerServer类
 *
 */
func (s *ChatSvr) Work(ctx context.Context, in *pb.BotRequest) (*pb.BotResponse, error) {
	//Detail request
	Psvr.Llog.Debug("------ Detail Request : \n\t%s", in.String())
	if in.BotName != s.botname {
		return nil, fmt.Errorf("botname not equal")
	}

	js, flag, err := ChatQueryProc(&RobotRequest{LogId: in.LogId,
		UserId:    in.UserId,
		Query:     in.Query,
		Timestamp: time.Now().Unix()})
	//组织返回
	content, _ := js.Encode()
	out := &pb.BotResponse{Status: 0, Score: 50}
	if err != nil {
		s.Llog.Error(err.Error())
	}
	if flag != 0 {
		//请求错误
		out.Status = pb.ReturnCode(flag)
	} else {
		//构造一张卡片
		out.ResItem = append(out.ResItem, &pb.BotResponse_ResultItem{Card: string(content)})
		out.Session = append(out.Session, &pb.UserSession{
			TableName:    s.botname,
			SessionKey:   "last",
			SessionValue: string(content),
		})
	}

	return out, nil
}
