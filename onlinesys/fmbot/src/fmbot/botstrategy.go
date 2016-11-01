package main

import (
	log "commonlib/beegologs"
	"commonlib/getwe/config"
	u "commonlib/getwe/utils"
	bot "gorpcimp/bot"
	se "gorpcimp/search"

	"encoding/json"
	"math/rand"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
)

// 状态机类型定义
type FmState int

const (
	START         FmState = 0 // 初始状态
	RECOM_ENSURE  FmState = 1 // 处理交互推荐item的状态
	RECOM_CONFIRM FmState = 2 // 推荐item需求明确状态
)

type BotState struct {
	currState FmState
}

func (bs *BotState) toJsonString() (string, error) {
	buf, err := json.Marshal(bs)
	if err != nil {
		return "", err
	}
	return string(buf), err
}

func (bs *BotState) fromJsonString(str string) error {
	return json.Unmarshal([]byte(str), bs)
}

// 一个协程处理一个业务逻辑的所有上下文数据
type BotStrategyData struct {
	// 最原始的输入
	botRequest *bot.BotRequest

	// 处理后最终要返回的结果
	botResponse *bot.BotResponse
}

// 业务处理逻辑.全局共用一个
type BotStrategy struct {
	// 配置相关只读
	// 下游地址列表
	fmseClientAddr []string

	// 文本相关性过滤阀值
	bweightFilt int32
}

func (sty *BotStrategy) Init(conf config.Conf) error {
	sty.fmseClientAddr = conf.StringArray("fmsearch.client")
	sty.bweightFilt = int32(conf.Int64Default("fmsearch.bweightFilt", 60))
	return nil
}

func (sty *BotStrategy) Run(request *bot.BotRequest) (*bot.BotResponse, error) {

	data := new(BotStrategyData)

	err := sty.parseRequest(data)
	if err != nil {
		return nil, u.ErrFmt("parseRequest fail : %s", err.Error())
	}

	err = sty.fmsearch(data)
	if err != nil {
		return nil, u.ErrFmt("fmsearchi fail : %s", err.Error())
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

// 请求fmsearch服务获取检索结果
func (sty *BotStrategy) fmsearch(data *BotStrategyData) error {

	addr := sty.fmseClientAddr[rand.Intn(len(sty.fmseClientAddr))]
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
		return u.ErrFmt("fmsearch fail")
	}

	for _, d := range response.ResList {
		if d.Bweight < sty.bweightFilt {
			log.Llog.Debug("bweight[%d] filt", d.Bweight)
			continue
		}
	}

	return nil
}

func (sty *BotStrategy) buildres(data *BotStrategyData) error {
	return nil
}
