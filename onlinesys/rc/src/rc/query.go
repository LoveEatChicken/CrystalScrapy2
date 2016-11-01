package main

import (
	"commonlib/simplejson"
	"errors"
	_ "fmt"
	_ "reflect"
	"time"
	//"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
	//"golang.org/x/net/context"
	pb "gorpcimp/bot"
	qu "gorpcimp/qu"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
)

/**
 *  连接mongodb的session定义
 *		Session::Content分为共享区Share和每个机器人的专用区ServiceName
 */
type AISession struct {
	Userid     string `bson:"userid"`
	CreateTime int64  `bson:"create_time"`
	UpdateTime int64  `bson:"update_time"`
	Content    string `bson:"content"`
}

//Session存储的MongoDB database和collection
const ConfSessionDB string = "iwant"
const ConfSessionTable string = "ai_session"

/**
 *	检索上下文，用于存储一次query检索过程的所有中间数据
 *
 */
type QueryContext struct {
	UserId    string                     //用户id
	Query     string                     //检索串
	LogId     string                     //统一日志id
	Intent    map[string]*pb.UserIntent  //QU识别的意图
	Requests  map[string]*pb.BotRequest  //所有下发的请求
	Results   map[string]*pb.BotResponse //所有下游返回的结果
	Hit       map[string]int             //对外输出的下游结果
	SceneName string                     //场景
}

const DefaultSceneName = "default" //默认场景名称

func NewQueryContext(botsize int, query string, userid string) *QueryContext {
	return &QueryContext{
		Query:     query,
		UserId:    userid,
		LogId:     Psvr.GenUniqueID("L"),
		Intent:    make(map[string]*pb.UserIntent, botsize),
		Requests:  make(map[string]*pb.BotRequest, botsize),
		Results:   make(map[string]*pb.BotResponse, botsize),
		Hit:       make(map[string]int, 1),
		SceneName: DefaultSceneName,
	}
}

/**
 *	处理ai/query请求
 *		请求qu模块，执行意图澄清
 *		一次请求下游服务模块，获取结果置信度打分
 *		二次请求下游服务模块，告知执行
 *
 *	接收请求格式如下:
 		{
			"userid":"aaaaa",
			"query":"今天天气怎么样啊？"
		}
*/
func AIQueryProc(jreq *simplejson.Json, iswhite int) (*simplejson.Json, int, error) {
	//解析请求
	userid, err := jreq.Get("userid").String()
	if err != nil {
		return nil, RCRequestFmtError, errors.New("Param userid missed.")
	}
	query, err := jreq.Get("query").String()
	if err != nil {
		return nil, RCRequestFmtError, errors.New("Param query missed.")
	}
	ctx := NewQueryContext(Psvr.BotSize, query, userid)

	//请求qu
	quresp := QuProc(ctx.Query, ctx.LogId)
	if quresp == nil {
		//qu失败了，请求所有下游
		Psvr.Llog.Error("Qu failed, what = response nil")
	} else {
		Psvr.Llog.Debug("Qu result as following:")
		Psvr.Llog.Debug("\t%s", quresp.String())
		for i1 := 0; i1 < len(quresp.QuRes); i1++ { //QuRes
			var intent []*pb.Intent
			for i2 := 0; i2 < len(quresp.QuRes[i1].Intent); i2++ { //Intent
				var slot []*pb.Slot
				for i3 := 0; i3 < len(quresp.QuRes[i1].Intent[i2].Slot); i3++ { //Slog
					slot = append(slot, &pb.Slot{
						Name:  quresp.QuRes[i1].Intent[i2].Slot[i3].Name,
						Value: quresp.QuRes[i1].Intent[i2].Slot[i3].Value,
					})
				}
				intent = append(intent, &pb.Intent{
					Score:     quresp.QuRes[i1].Intent[i2].Score,
					ExtraAttr: quresp.QuRes[i1].Intent[i2].ExtraAttr,
					Slot:      slot,
				})
			}
			ctx.Intent[quresp.QuRes[i1].Domain] = &pb.UserIntent{Intent: intent}
		}
	}

	//请求Session
	mpsess, jsess, isnew := GetSession(userid, ctx.LogId)

	//一次请求 : 获取所有要请求的下游
	svrs := make([]*BotService, 0, Psvr.BotSize)
	Psvr.mu.RLock()
	for botname, item := range Psvr.Service {
		Psvr.Llog.Debug("Add bot : [%s][%s]", botname, item.Address)
		svrs = append(svrs, item)

		//构建请求
		req := &pb.BotRequest{
			BotName:     botname,
			LogId:       ctx.LogId,
			UserId:      userid,
			RequestType: pb.RequestType_ENQUIRE,
			Query:       query,
		}
		_, ok := ctx.Intent[botname]
		if ok {
			req.Intent = ctx.Intent[botname]
		}
		_, ok = mpsess[botname]
		if ok {
			req.Session = mpsess[botname]
			Psvr.Llog.Debug("Session[%s] : ", botname)
			for jter := 0; jter < len(mpsess[botname]); jter++ {
				Psvr.Llog.Debug("\t%s", mpsess[botname][jter].String())
			}
		}
		_, ok = mpsess["share"]
		if ok {
			req.Session = append(req.Session, mpsess["share"]...)
			Psvr.Llog.Debug("Session[share] : ")
			for jter := 0; jter < len(mpsess["share"]); jter++ {
				Psvr.Llog.Debug("\t%s", mpsess["share"][jter].String())
			}
		}
		ctx.Requests[botname] = req
		ctx.Results[botname] = &pb.BotResponse{Status: pb.ReturnCode_NULLDATA}
	}
	Psvr.mu.RUnlock()
	//构建channel用于响应召回,每个子协程自己控制超时
	wait := make(chan int, len(svrs))
	defer close(wait)
	for i := 0; i < len(svrs); i++ {
		Psvr.Llog.Debug("i = %d : go ServiceProc(%d)", i, ctx.Requests[svrs[i].BotName].RequestType)
		go ServiceProc(wait, i, svrs[i], ctx)

	}
	//等待所有service返回结果
	for iter := 0; iter < len(svrs); iter++ {
		<-wait //阻塞在wait
	}

	//排序,选择要输出的结果
	Rank(ctx)

	//二次请求:确定采纳某些个下游结果
	for i := 0; i < len(svrs); i++ {
		ctx.Requests[svrs[i].BotName].RequestType = pb.RequestType_CONFIRM
		if svrs[i].IsRepeated == 0 {
			Psvr.Llog.Debug("svr[%s] request only once!!!", svrs[i].BotName)
			wait <- i
			continue
		}
		_, ok := ctx.Hit[svrs[i].BotName]
		if !ok {
			Psvr.Llog.Debug("svr[%s] request dropped!!!", svrs[i].BotName)
			wait <- i
			continue
		}
		Psvr.Llog.Debug("i = %d : go ServiceProc(%d)", i, int(ctx.Requests[svrs[i].BotName].RequestType))
		go ServiceProc(wait, i, svrs[i], ctx)
	}
	//等待所有service返回结果
	for iter := 0; iter < len(svrs); iter++ {
		<-wait //阻塞在wait
	}

	//回写Session
	err = SetSession(ctx, jsess, isnew)

	//渲染结果
	if iswhite == 1 {
		jresp, err := RenderWhite(ctx)
		if err != nil {
			return nil, RCSystemError, err
		}
		return jresp, 0, nil
	} else {
		jresp, err := RenderResult(ctx)
		if err != nil {
			return nil, RCSystemError, err
		}
		return jresp, 0, nil
	}
}

//请求Qu,阻塞
func QuProc(query string, logid string) *qu.QuServerResponse {
	//捕捉异常,不能影响主进程
	defer func() {
		if r := recover(); r != nil {
			Psvr.Llog.Error("catch panic : %s", r)
		}
	}()

	//构建访问client
	if Psvr.Qu.C == nil {
		Psvr.Llog.Debug("Start to connect : Qu:%s", Psvr.Qu.Address)
		conn, err := grpc.Dial(Psvr.Qu.Address,
			grpc.WithTimeout(time.Second*time.Duration(Psvr.Qu.Timeout)),
			grpc.WithInsecure(),
			grpc.WithBlock())
		if err != nil {
			Psvr.Llog.Error("Connect failed.")
			conn.Close()
			return nil
		} else {
			Psvr.Llog.Debug("Connect succeed.")
			Psvr.Qu.C = qu.NewQuServerClient(conn)
		}
	} else {
		Psvr.Llog.Debug("Connect reused.")
	}
	//业务逻辑
	req := &qu.QuServerRequest{
		LogId:  logid,
		Query:  query,
		Domain: Psvr.DomainList,
	}
	resp, err := Psvr.Qu.C.Parse(context.Background(), req)
	if err != nil {
		Psvr.Llog.Error("Request [%s:qu:%s] failed. what = %v",
			logid, query, err)
		return nil
	}
	return resp
}

//请求Session：读取MongoDB,将Session按照BotRequest来分发
func GetSession(userid string, logid string) (map[string][]*pb.UserSession, *simplejson.Json, bool) {
	mpsess := make(map[string][]*pb.UserSession)
	ms := Psvr.GetMgoSession()
	defer ms.Close()
	c := ms.DB(ConfSessionDB).C(ConfSessionTable)
	result := AISession{}
	err := c.Find(bson.M{"userid": userid}).One(&result)
	if err != nil {
		Psvr.Llog.Error("[%s] Get [%s]'Session failed, what = %v", logid, userid, err)
		return mpsess, simplejson.New(), true //空map
	}
	jcot, err := simplejson.NewJson([]byte(result.Content))
	if err != nil {
		Psvr.Llog.Error("[%s] Parse [%s]'Session failed, what = %v", logid, userid, err)
		return mpsess, simplejson.New(), true //空map
	}
	//获取share区session
	_, err = jcot.Map()
	if err != nil {
		Psvr.Llog.Debug("NotMap : %s, what = %v", result.Content, err)
	} else {
		Psvr.Llog.Debug("Map : %s", result.Content)
	}
	for botname, item := range jcot.MustMap() {
		//session := &simplejson.Json{data: item}
		session, ok := item.(map[string]interface{})
		if !ok {
			continue
		}
		tmparr := make([]*pb.UserSession, 0, 1)
		for key, value := range session {
			if str_value, ok := value.(string); ok {
				tmparr = append(tmparr, &pb.UserSession{
					TableName:    botname,
					SessionKey:   key,
					SessionValue: str_value,
				})
			}
		}
		mpsess[botname] = tmparr
	}
	return mpsess, jcot, false
}

//更新Session:将下游Session更新回原Session表
func SetSession(ctx *QueryContext, jsess *simplejson.Json, isnew bool) error {
	ms := Psvr.GetMgoSession()
	defer ms.Close()
	c := ms.DB(ConfSessionDB).C(ConfSessionTable)
	for _, res := range ctx.Results {
		for j := 0; j < len(res.Session); j++ {
			jsess.SetPath([]string{res.Session[j].TableName, res.Session[j].SessionKey},
				res.Session[j].SessionValue)
		}
	}
	content, err := jsess.Encode()
	if err != nil {
		Psvr.Llog.Error("[%s]Encode [%s]'s Jsess failed, what = %v", ctx.LogId, ctx.UserId, err)
		return err
	}
	Psvr.Llog.Debug("New Session = %s", string(content))
	now := time.Now()
	if isnew {
		psess := &AISession{
			Userid:     ctx.UserId,
			Content:    string(content),
			CreateTime: now.Unix(),
			UpdateTime: now.Unix(),
		}
		err := c.Insert(psess)
		if err != nil { //更新失败
			Psvr.Llog.Error("[%s]Insert [%s]'s Session failed, what = %v", ctx.LogId, ctx.UserId, err)
			return err
		}
	} else {
		up := bson.M{}
		up["update_time"] = now.Unix()
		up["content"] = string(content)
		err := c.Update(bson.M{"userid": ctx.UserId}, bson.M{"$set": up})
		if err != nil {
			//更新DB失败，不要更新内存
			Psvr.Llog.Error("[%s]Update [%s]'s Session failed, what = %v", ctx.LogId, ctx.UserId, err)
			return err
		}
	}

	return nil
}

//向下游分发请求
func ServiceProc(wait chan int, i int, service *BotService, ctx *QueryContext) {
	//捕捉异常,不能影响主进程
	defer func() {
		if r := recover(); r != nil {
			if service == nil {
				Psvr.Llog.Error("invalid service, i = %d", i)
			} else {
				Psvr.Llog.Error("[%s]Catch panic : %s\n", service.BotName, r)
			}
			wait <- i
			return
		}
	}()

	//构建访问client
	if service.C == nil {
		Psvr.Llog.Debug("[%s]Start to connect :%s", service.BotName, service.Address)
		conn, err := grpc.Dial(service.Address,
			grpc.WithTimeout(time.Second*time.Duration(service.Timeout)),
			grpc.WithInsecure(),
			grpc.WithBlock())
		if err != nil {
			Psvr.Llog.Error("[%s]Connect failed.", service.BotName)
			conn.Close()
			wait <- i
			return
		} else {
			Psvr.Llog.Debug("[%s]Connect succeed.", service.BotName)
			service.C = pb.NewBotServerClient(conn)
		}
	} else {
		Psvr.Llog.Debug("[%s]Connect reused.", service.BotName)
	}

	//业务逻辑
	Psvr.Llog.Debug("Request as following : \n\t\t%s", ctx.Requests[service.BotName].String())
	r, err := service.C.Work(context.Background(), ctx.Requests[service.BotName])
	if err != nil {
		Psvr.Llog.Error("Request [%s:%s:%s] failed. what = %v",
			ctx.LogId, service.BotName, ctx.Query, err)
		wait <- i
		return
	}
	ctx.Results[service.BotName] = r //替换结果
	wait <- i
	return
}

/**
 *	从所有结果中选择置信度最高的一条
 *
 */
func Rank(ctx *QueryContext) {
	asb := func(val int) int {
		if val < 0 {
			return val * -1
		}
		return val
	}
	//提取scene
	scene, ok := Psvr.Scene[ctx.SceneName]
	if !ok {
		scene = Psvr.Scene[DefaultSceneName]
	}
	rsvd_bot := make([]int, 0, 1)
	for i := 0; i < len(scene.BotLevel); i++ {
		botname := scene.BotLevel[i].BotName
		level := scene.BotLevel[i].Level
		if ctx.Results[botname].Status != 0 {
			continue
		}
		if ctx.Results[botname].Score >= int32(Psvr.Service[botname].Sty.Higher) {
			if len(rsvd_bot) <= 0 {
				//直接采纳
				ctx.Hit[botname] = 1
				break
			} else {
				level_minus := asb(scene.BotLevel[rsvd_bot[0]].Level - level)
				if level_minus <= Psvr.Service[scene.BotLevel[rsvd_bot[0]].BotName].Sty.ReplaceLevel {
					//在可替换范围内
					ctx.Hit[botname] = 1
					break
				}
			}
			rsvd_bot = append(rsvd_bot, i) //加入候选集合
		} else if ctx.Results[botname].Score < int32(Psvr.Service[botname].Sty.Lower) {
			//丢弃
			continue
		} else {
			//加入候选集合
			if len(rsvd_bot) <= 0 {
				rsvd_bot = append(rsvd_bot, i)
				continue
			}
			level_minus := asb(scene.BotLevel[rsvd_bot[0]].Level - level)
			if level_minus <= Psvr.Service[scene.BotLevel[rsvd_bot[0]].BotName].Sty.ReplaceLevel {
				//在可替换范围内,加入候选集合
				rsvd_bot = append(rsvd_bot, i)
			}
		}
	}
	if len(ctx.Hit) <= 0 {
		if len(rsvd_bot) <= 0 {
			//无结果
			return
		} else {
			ctx.Hit[scene.BotLevel[rsvd_bot[0]].BotName] = 1
			return
		}
	}
	return
}

/**
 *	渲染结果为json
 *	正常结果
 */
func RenderResult(ctx *QueryContext) (*simplejson.Json, error) {
	count := 0
	jresp := simplejson.New()
	jlist := make([]*simplejson.Json, 0, Psvr.BotSize)
	for botname, res := range ctx.Results {
		if res.Status != 0 {
			Psvr.Llog.Error("Request [%s:%s:%s] failed", ctx.LogId, botname, ctx.Query)
			continue
		}
		_, ok := ctx.Hit[botname]
		if !ok { //结果没有采纳
			Psvr.Llog.Debug("Request [%s:%s:%s] droppped", ctx.LogId, botname, ctx.Query)
		} else {
			Psvr.Llog.Debug("Request [%s:%s:%s] success, score = %d",
				ctx.LogId, botname, ctx.Query, res.Score)
			jitem := simplejson.New()
			jitem.Set("score", res.Score)
			reslist := make([]*simplejson.Json, 0, 5)
			for _, item := range res.ResItem {
				Psvr.Llog.Debug("\tCard = [%s]", item.Card)
				jres := simplejson.New()
				jcard, err := simplejson.NewJson([]byte(item.Card))
				if err != nil {
					jres.Set("card", item.Card)
				} else {
					jres.Set("card", jcard)
				}
				reslist = append(reslist, jres)
			}
			jitem.Set("result", reslist)
			guidlist := make([]*simplejson.Json, 0, 5)
			for _, gd := range res.Guide {
				Psvr.Llog.Debug("\tText = [%s]", gd.Text)
				jgd := simplejson.New()
				jtmp, err := simplejson.NewJson([]byte(gd.Text))
				if err != nil {
					jgd.Set("text", gd.Text)
				} else {
					jgd.Set("text", jtmp)
				}
				guidlist = append(guidlist, jgd)
			}
			jitem.Set("guide", guidlist)
			jlist = append(jlist, jitem)
			count += 1
		}
	}
	jresp.Set("sum", count)
	jresp.Set("list", jlist)
	return jresp, nil
}

//将请求转化为json格式
func Request2Json(ctx *QueryContext, botname string) *simplejson.Json {
	jitem := simplejson.New()
	req := ctx.Requests[botname]
	jsess := make([]*simplejson.Json, 0, 1)
	for i := 0; i < len(req.Session); i++ {
		ji := simplejson.New()
		ji.Set("name", req.Session[i].TableName)
		ji.Set("key", req.Session[i].SessionKey)
		ji.Set("value", req.Session[i].SessionValue)
		jsess = append(jsess, ji)
	}
	jitem.Set("session", jsess)
	if req.Intent == nil {
		jitem.Set("intent", nil)
	} else {
		jlint := make([]*simplejson.Json, 0, 1)
		for i := 0; i < len(req.Intent.Intent); i++ {
			jint := simplejson.New()
			jint.Set("score", req.Intent.Intent[i].Score)
			jint.Set("extra", req.Intent.Intent[i].ExtraAttr)
			jslot := make([]*simplejson.Json, 0, 1)
			for j := 0; j < len(req.Intent.Intent[i].Slot); j++ {
				jj := simplejson.New()
				jj.Set("name", req.Intent.Intent[i].Slot[j].Name)
				jj.Set("value", req.Intent.Intent[i].Slot[j].Value)
				jslot = append(jslot, jj)
			}
			jint.Set("slot", jslot)
			jlint = append(jlint, jint)
		}
		jitem.Set("intent", jlint)
	}
	return jitem
}

//将响应结果转化为json格式
func Response2Json(ctx *QueryContext, botname string) *simplejson.Json {
	res := ctx.Results[botname]
	jitem := simplejson.New()
	jitem.Set("Status", res.Status)
	if res.Status != 0 {
		return jitem
	}
	_, ok := ctx.Hit[botname]
	if ok {
		jitem.Set("rank", 1)
	} else {
		jitem.Set("rank", 0)
	}
	jitem.Set("score", res.Score)
	reslist := make([]*simplejson.Json, 0, 5)
	for _, item := range res.ResItem {
		jres := simplejson.New()
		jcard, err := simplejson.NewJson([]byte(item.Card))
		if err != nil {
			jres.Set("card", item.Card)
		} else {
			jres.Set("card", jcard)
		}
		reslist = append(reslist, jres)
	}
	jitem.Set("result", reslist)
	guidlist := make([]*simplejson.Json, 0, 5)
	for _, gd := range res.Guide {
		jgd := simplejson.New()
		jtmp, err := simplejson.NewJson([]byte(gd.Text))
		if err != nil {
			jgd.Set("text", gd.Text)
		} else {
			jgd.Set("text", jtmp)
		}
		guidlist = append(guidlist, jgd)
	}
	jitem.Set("guide", guidlist)
	return jitem
}

/**
 *	渲染结果为json
 *	白板结果
 */
func RenderWhite(ctx *QueryContext) (*simplejson.Json, error) {

	jresp := simplejson.New()
	//提取场景
	scene, ok := Psvr.Scene[ctx.SceneName]
	if !ok {
		scene = Psvr.Scene[DefaultSceneName]
	}
	jitem := simplejson.New()
	jitem.Set("name", scene.SceneName)
	for i := 0; i < len(scene.BotLevel); i++ {
		botname := scene.BotLevel[i].BotName
		//jitem.Set(botname) = scene.BotLevel[i].Level
		kitem := simplejson.New()
		kitem.Set("level", scene.BotLevel[i].Level)
		kitem.Set("higher", Psvr.Service[botname].Sty.Higher)
		kitem.Set("lower", Psvr.Service[botname].Sty.Lower)
		kitem.Set("replace_level", Psvr.Service[botname].Sty.ReplaceLevel)
		jitem.Set(botname, kitem)
	}
	jresp.Set("scene", jitem)
	jresp.Set("logid", ctx.LogId)
	jresp.Set("userid", ctx.UserId)
	jresp.Set("query", ctx.Query)
	//请求和响应
	jlist := make([]*simplejson.Json, 0, Psvr.BotSize)
	count := 0
	for botname, _ := range ctx.Results {
		jitem := simplejson.New()
		jitem.Set("botname", botname)
		jitem.Set("request", Request2Json(ctx, botname))
		jitem.Set("response", Response2Json(ctx, botname))
		jlist = append(jlist, jitem)
		count += 1
	}
	jresp.Set("sum", count)
	jresp.Set("list", jlist)
	return jresp, nil
}
