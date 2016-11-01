package main

import (
	log "commonlib/beegologs"
	botkit "commonlib/botkit"
	"commonlib/getwe/config"
	u "commonlib/getwe/utils"
	json "commonlib/simplejson"
	bot "gorpcimp/bot"
	se "gorpcimp/search"

	"math/rand"
	"strings"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
)

// 一个协程处理一个业务逻辑的所有上下文数据
type BotStrategyData struct {
	// 最原始的输入
	botRequest *bot.BotRequest

	// 处理后最终要返回的结果
	botResponse *bot.BotResponse

	// 搜索后本地要返回的文档
	seRetDoc []*json.Json
}

// 业务处理逻辑.全局共用一个
type BotStrategy struct {
	// 配置相关只读
	// 下游地址列表
	qaseClientAddr []string

	// 文本相关性过滤阀值
	bweightFilt int32
}

func (sty *BotStrategy) Init(conf config.Conf) error {
	sty.qaseClientAddr = conf.StringArray("qasearch.client")
	sty.bweightFilt = int32(conf.Int64Default("qasearch.bweightFilt", 60))
	return nil
}

func (sty *BotStrategy) Run(request *bot.BotRequest) (*bot.BotResponse, error) {

	data := new(BotStrategyData)
	data.botRequest = request

	err := sty.parseRequest(data)
	if err != nil {
		return nil, u.ErrFmt("parseRequest fail : %s", err.Error())
	}

	err = sty.qasearch(data)
	if err != nil {
		return nil, u.ErrFmt("qasearchi fail : %s", err.Error())
	}

	err = sty.buildres(data)
	if err != nil {
		return nil, u.ErrFmt("buildres fail : %s", err.Error())
	}

	return data.botResponse, nil
}

func (sty *BotStrategy) parseRequest(data *BotStrategyData) error {

	log.Llog.Info("LogId[%s] query[%s] RequestType[%d]",
		data.botRequest.LogId,
		data.botRequest.Query,
		data.botRequest.RequestType)
	return nil
}

// 请求qasearch服务获取检索结果
func (sty *BotStrategy) qasearch(data *BotStrategyData) error {

	addr := sty.qaseClientAddr[rand.Intn(len(sty.qaseClientAddr))]
	conn, err := grpc.Dial(addr, grpc.WithInsecure())
	defer conn.Close()
	if err != nil {
		return err
	}

	client := se.NewSearcherClient(conn)
	request := new(se.SeRequest)
	request.PageNum = 0
	request.PageSize = 10
	request.IsDebug = false
	request.LogId = data.botRequest.LogId
	request.Query = data.botRequest.Query

	response, err := client.Search(context.Background(), request)
	if err != nil {
		return err
	}

	// parse response
	if response.RetNum == 0 || len(response.ResList) == 0 {
		return u.ErrFmt("qasearch fail")
	}

	data.seRetDoc = make([]*json.Json, 0)

	for i, d := range response.ResList {
		if d.Bweight < sty.bweightFilt {
			log.Llog.Debug("bweight[%d] filt", d.Bweight)
			continue
		}
		obj, err := json.NewFromReader(strings.NewReader(d.Data))
		if err != nil {
			log.Llog.Warn("doc[%d] [%s] load as json fail", i, d.Data)
			continue
		}
		data.seRetDoc = append(data.seRetDoc, obj)
	}

	return nil
}

func (sty *BotStrategy) buildres(data *BotStrategyData) error {

	// build result
	data.botResponse = new(bot.BotResponse)
	if len(data.seRetDoc) == 0 {
		return u.ErrFmt("no search result")
	}

	display := botkit.NewBotDisplay(data.botResponse)
	display.AddCardShortText("知识库检索结果：") // TODO debug

	// TODO
	// 返回第一个结果,后续修改返回更多结果
	obj := data.seRetDoc[0]
	question := obj.Get("question").MustString("<nil>")
	answer := obj.Get("answer").MustString("<nil>")
	url := "https://www.baidu.com"
	err := display.AddCardQAAnswer(question, answer, url)
	if err != nil {
		log.Llog.Warn(err.Error())
		return u.ErrFmt("build res fail")
	}

	// build guide
	return nil
}
