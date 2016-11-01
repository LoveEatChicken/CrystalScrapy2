package main

import (
	"commonlib/logs"
	_ "commonlib/mysql"
	"commonlib/simplejson"
	"database/sql"
	"fmt"
	pb "gorpcimp/bot"
	qu "gorpcimp/qu"
	"net/http"
	"os"
	"reflect"
	"sync"
	"time"

	"github.com/achun/tom-toml"
	"gopkg.in/mgo.v2"
)

const (
	ReportCmdQueryFailed = "97001" //请求失败
)

//多个垂类结果的rank策略
type RankStrategy struct {
	Higher       int //好结果打分下限
	Lower        int //可收录结果打分下限
	DefaultLevel int //Bot的默认优先级：数值从高到地
	ReplaceLevel int //可替换优先级
}

//下游服务配置
type BotService struct {
	BotName    string             //服务名称
	Address    string             //访问地址
	Session    string             //Session名称
	Timeout    int                //发送超时
	IsRepeated int                //二次下发：0=no;1=yes
	C          pb.BotServerClient //请求载体
	Sty        RankStrategy       //排序策略树
}

//场景内Bot优先级排序
type SceneBotLevel struct {
	BotName string //机器人ID
	Level   int    //优先级
}

//场景优先级定义
type SceneStrategy struct {
	SceneName string           //场景id
	BotLevel  []*SceneBotLevel //场景下Bot优先级排序
}

//qu服务配置
type QueryUnderstanding struct {
	Address string            //访问地址
	Timeout int               //发送超时
	C       qu.QuServerClient //请求载体
}

type RCSvr struct {
	confFile string    //保存配置文件路径,便于重新加载配置(TOML格式)
	conf     toml.Toml //配置句柄,从中获取配置数据

	//mgo session池
	MgoPool chan *mgo.Session

	//mysql连接池
	DB *sql.DB

	//log句柄 : 系统日志 & 远程业务日志
	Llog *logs.BeeLogger //系统日志：本地文件

	//http 服务器
	bindAddr     string
	readTimeout  int
	writeTimeout int
	svr          *http.Server //服务器框架

	//定义一个全局锁，用于控制执行次序
	mu sync.RWMutex

	//业务数据部分
	BotSize    int
	Service    map[string]*BotService //下游服务
	DomainList []string
	Scene      map[string]*SceneStrategy //场景策略

	Qu QueryUnderstanding //意图理解

	//进程ID
	PID         int
	SessionIter int64
	ProcSuffix  int //服务器下标
}

/**
 *  初始化服务器
 *      @param confFile 配置文件 ini
 *
 *
 */
func (ds *RCSvr) Init() error {
	//初始化不允许出现异常
	defer func() {
		if r := recover(); r != nil {
			fmt.Printf("Catch panic : %s\n", r)
			os.Exit(-1)
		}
	}()

	ds.PID = os.Getpid()
	ds.SessionIter = 0

	var err error = nil
	//解析配置文件
	ds.conf, err = toml.LoadFile(ds.confFile)
	if err != nil {
		return err
	}

	//初始化日志
	err = ds.initlog()
	if err != nil {
		return err
	}
	ds.Llog.Info("--------------------- Service initial -------------------------")

	//初始化mgo
	ds.Llog.Info("------ Init mgo ------")
	err = ds.initmgo()
	if err != nil {
		return err
	}

	//初始化mysql
	ds.Llog.Info("------ Init mysql ------")
	err = ds.initdb()
	if err != nil {
		return err
	}

	//初始化QU
	ds.Llog.Info("------ Init Qu -------")
	err = ds.initqu()
	if err != nil {
		return err
	}

	//初始化下游
	ds.Llog.Info("------ Init bot ------")
	err = ds.initbot()
	if err != nil {
		return err
	}

	//初始化场景
	ds.Llog.Info("------ Init Scene -----")
	err = ds.initscene()
	if err != nil {
		return err
	}

	//初始化服务器
	ds.Llog.Info("------ Init Task ------")
	ds.bindAddr = ds.conf["task.bind_addr"].String()
	ds.readTimeout = ds.conf["task.read_timeout"].Integer()
	ds.writeTimeout = ds.conf["task.write_timeout"].Integer()
	ds.Llog.Info("bind : %s", ds.bindAddr)
	ds.Llog.Info("ReadTimeOut : %d", ds.readTimeout)
	ds.Llog.Info("WriteTimeOut : %d", ds.writeTimeout)
	ds.svr = &http.Server{
		Addr: ds.bindAddr,
		//Handler: http.NewServeMux(),  //使用DefaultServeMux
		ReadTimeout:    time.Second * time.Duration(ds.readTimeout),
		WriteTimeout:   time.Second * time.Duration(ds.writeTimeout),
		MaxHeaderBytes: 1 << 20,
	}

	//初始化业务数据
	ds.ProcSuffix = ds.conf["task.svr_suffix"].Integer()
	ds.Llog.Info("--------------------- Service running -------------------------")
	return nil

}

//启动服务器
func (ds *RCSvr) Run() {
	err := ds.svr.ListenAndServe()
	if err != nil {
		return
	}

	return
}

//初始化日志服务
func (ds *RCSvr) initlog() error {
	local_log_channel := ds.conf["log.locallog.max_channel_size"].Integer()
	llog_name := ds.conf["log.locallog.filename"].String()
	llog_level := ds.conf["log.locallog.level"].Integer()
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

//初始化mgo
func (ds *RCSvr) initmgo() error {
	//初始化mgo
	max_session_size := ds.conf["mongodb.max_session_size"].Integer()
	ds.Llog.Info("max_session_size = %d", max_session_size)
	ds.MgoPool = make(chan *mgo.Session, max_session_size)
	addr := ds.conf["mongodb.addr"].String()
	for i := 0; i < max_session_size; i++ {
		//建立 N 个session
		session, err := mgo.Dial(addr)
		if err != nil {
			return err //不允许失败
		}
		ds.MgoPool <- session
	}

	return nil
}

//初始化数据库
func (ds *RCSvr) initdb() error {
	dns := ds.conf["mysql.dns"].String()
	var err error
	ds.DB, err = sql.Open("mysql", dns)
	if err != nil {
		ds.Llog.Error("Connect mysql failed, dns = %s", dns)
	}

	return nil
}

//初始化Qu
func (ds *RCSvr) initqu() error {
	ds.Qu.Timeout = ds.conf["qu.timeout"].Integer()
	ds.Qu.Address = ds.conf["qu.address"].String()
	if ds.Qu.Address == "" {
		panic("without qu model")
	}
	ds.Qu.C = nil
	ds.Llog.Info("Add qu = %s, %d", ds.Qu.Address, ds.Qu.Timeout)

	return nil
}

//初始化垂类
func (ds *RCSvr) initbot() error {
	botarr := ds.conf["bots"].TomlArray()
	ds.BotSize = botarr.Len()
	if ds.BotSize <= 0 {
		panic("no service")
	}
	ds.DomainList = make([]string, ds.BotSize)
	ds.Service = make(map[string]*BotService)
	for i := 0; i < ds.BotSize; i++ {
		botname := botarr[i]["name"].String()
		ds.Service[botname] = &BotService{
			BotName:    botname,
			Address:    botarr[i]["addr"].String(),
			Session:    botarr[i]["session"].String(),
			Timeout:    botarr[i]["timeout"].Integer(),
			IsRepeated: botarr[i]["repeated"].Integer(),
			C:          nil,
			Sty: RankStrategy{
				Higher:       botarr[i].Fetch("rank")["higher"].Integer(),
				Lower:        botarr[i].Fetch("rank")["lower"].Integer(),
				DefaultLevel: botarr[i].Fetch("rank")["default_level"].Integer(),
				ReplaceLevel: botarr[i].Fetch("rank")["replace_level"].Integer(),
			},
		}
		ds.DomainList = append(ds.DomainList, botname)
	}
	for botname, item := range ds.Service {
		ds.Llog.Info("Add Service : name=%s, addr=%s, session=%s,timeout=%d",
			botname, item.Address, item.Session, item.Timeout)
		ds.Llog.Info("\tRank Strategy : Higher=%d,Lower=%d,DefaultLevel=%d,ReplaceLevel=%d",
			item.Sty.Higher, item.Sty.Lower, item.Sty.DefaultLevel, item.Sty.ReplaceLevel)
	}

	return nil
}

//初始化场景
func (ds *RCSvr) initscene() error {
	ds.Scene = make(map[string]*SceneStrategy)
	//加载配置场景排序策略
	sarr := ds.conf["scene"].TomlArray()
	for i := 0; i < sarr.Len(); i++ {
		scene := &SceneStrategy{
			SceneName: sarr[i]["name"].String(),
			BotLevel:  make([]*SceneBotLevel, 0, 1),
		}
		botarr := sarr[i]["bot"].TomlArray()
		for j := 0; j < botarr.Len(); j++ {
			item := &SceneBotLevel{
				BotName: botarr[j]["name"].String(),
				Level:   botarr[j]["level"].Integer(),
			}
			flag := 0
			for k := 0; k < len(scene.BotLevel); k++ {
				if scene.BotLevel[k].Level < item.Level {
					//中间插入
					nlevl := make([]*SceneBotLevel, 0, ds.BotSize)
					if k > 0 {
						nlevl = append(nlevl, scene.BotLevel[:k]...)
					}
					nlevl = append(nlevl, item)
					nlevl = append(nlevl, scene.BotLevel[k:]...)
					scene.BotLevel = nlevl
					flag = 1
					break
				}
			}
			if flag == 0 {
				scene.BotLevel = append(scene.BotLevel, item)
			}
		}
		ds.Scene[scene.SceneName] = scene
	}
	//添加默认场景排序策略
	scene := &SceneStrategy{
		SceneName: DefaultSceneName,
		BotLevel:  make([]*SceneBotLevel, 0, 1),
	}
	for botname, bot := range ds.Service {
		item := &SceneBotLevel{
			BotName: botname,
			Level:   bot.Sty.DefaultLevel,
		}
		flag := 0
		for k := 0; k < len(scene.BotLevel); k++ {
			if scene.BotLevel[k].Level < item.Level {
				//中间插入
				nlevl := make([]*SceneBotLevel, 0, ds.BotSize)
				if k > 0 {
					nlevl = append(nlevl, scene.BotLevel[:k]...)
				}
				nlevl = append(nlevl, item)
				nlevl = append(nlevl, scene.BotLevel[k:]...)
				scene.BotLevel = nlevl
				flag = 1
				break
			}
		}
		if flag == 0 {
			scene.BotLevel = append(scene.BotLevel, item)
		}
	}
	ds.Scene[scene.SceneName] = scene

	//打印输出日志
	for name, item := range ds.Scene {
		ds.Llog.Info("Add Scene : name=%s", name)
		for i := 0; i < len(item.BotLevel); i++ {
			ds.Llog.Info("\tBotLevel : name=%s,level=%d",
				item.BotLevel[i].BotName,
				item.BotLevel[i].Level)
		}
	}

	return nil
}

//注册业务函数
func (ds *RCSvr) Register(path string, handler func(http.ResponseWriter, *http.Request)) {
	http.HandleFunc(path, handler)
	ds.Llog.Info("Register [%s] To func[%s]", path, reflect.ValueOf(handler).String())
}

//获取Session
func (ds *RCSvr) GetMgoSession() *mgo.Session {
	fms := <-ds.MgoPool
	defer func(fms *mgo.Session) {
		ds.MgoPool <- fms
	}(fms)
	ms := fms.Copy()
	return ms
}

//构造全局唯一的ID
func (ds *RCSvr) GenUniqueID(prefix string) string {
	iter := ds.SessionIter
	ds.SessionIter++
	return fmt.Sprintf("%s%d%05d%d", prefix, time.Now().Unix(), ds.ProcSuffix, iter%100000)
}

//业务日志上报
func (ds *RCSvr) TaskReport2Log(cmd string, args []interface{}) {
	logstr := fmt.Sprintf("\t%d\t%s", time.Now().Unix(), cmd)
	for i := 0; i < len(args); i++ {
		switch args[i].(type) {
		case string:
			str_val, _ := args[i].(string)
			logstr += "\t" + str_val
		case int:
			int_val, _ := args[i].(int)
			logstr += "\t" + fmt.Sprintf("%d", int_val)
		case float64:
			float_val, _ := args[i].(float64)
			logstr += "\t" + fmt.Sprintf("%f", float_val)
		case int64:
			i64_val, _ := args[i].(int64)
			logstr += "\t" + fmt.Sprintf("%d", i64_val)
		default:
			logstr += "\t "
		}
	}
	//TODO : ds.Nlog.Info(logstr)
}
