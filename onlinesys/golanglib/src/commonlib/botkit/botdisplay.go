package botkit

import (
	json "commonlib/simplejson"
	bot "gorpcimp/bot"
)

type StringPair struct {
	arg1 string
	arg2 string
}

// 辅助各个bot用来进行卡片的渲染
// https://www.tapd.cn/20059351/markdown_wikis/#1120059351001000111
// 成员变量保存*bot.BotResponse,该类实例不可并发访问
type BotDisplay struct {
	BotResponse *bot.BotResponse
}

func NewBotDisplay(res *bot.BotResponse) *BotDisplay {
	dsp := new(BotDisplay)
	dsp.BotResponse = res
	if dsp.BotResponse.ResItem == nil {
		dsp.BotResponse.ResItem = make([]*bot.BotResponse_ResultItem, 0)
	}

	if dsp.BotResponse.Guide == nil {
		dsp.BotResponse.Guide = make([]*bot.BotResponse_Guide, 0)
	}
	return dsp
}

func (dsp *BotDisplay) AddCardJson(obj *json.Json) error {
	buf, _ := obj.Encode()

	item := new(bot.BotResponse_ResultItem)
	item.Card = string(buf)

	dsp.BotResponse.ResItem = append(dsp.BotResponse.ResItem, item)
	return nil
}

// 增加一个短文本卡片
func (dsp *BotDisplay) AddCardShortText(text string) error {
	obj := json.New()
	obj.Set("cardName", "shorttext")
	obj.Set("content", text)
	return dsp.AddCardJson(obj)
}

// 增加一个长文本卡片
func (dsp *BotDisplay) AddCardLongText(text []string, url string) error {
	obj := json.New()
	obj.Set("cardName", "longtext")
	obj.Set("contentArray", text)
	obj.Set("linkUrl", url)
	return dsp.AddCardJson(obj)
}

// 增加问答类答案卡片
func (dsp *BotDisplay) AddCardQAAnswer(title, content, linkUrl string) error {
	obj := json.New()
	obj.Set("cardName", "qa-answer")
	obj.Set("title", title)
	obj.Set("content", content)
	obj.Set("linkUrl", linkUrl)
	return dsp.AddCardJson(obj)
}

// 增加实体Item卡片
func (dsp *BotDisplay) AddCardEntityItem(img, title, linkUrl string,
	attr []StringPair) error {
	obj := json.New()
	obj.Set("cardName", "entityitem")
	obj.Set("img", img)
	obj.Set("title", title)
	obj.Set("linkUrl", linkUrl)
	attribute := make([]*json.Json, 0)
	for _, p := range attr {
		a := json.New()
		a.Set("name", p.arg1)
		a.Set("value", p.arg2)
		attribute = append(attribute, a)
	}
	obj.Set("attribute", attribute)
	return dsp.AddCardJson(obj)
}

// 增加一个guide选项
func (dsp *BotDisplay) AddGuide(text string) error {

	guide := new(bot.BotResponse_Guide)
	guide.Text = text

	dsp.BotResponse.Guide = append(dsp.BotResponse.Guide, guide)
	return nil
}
