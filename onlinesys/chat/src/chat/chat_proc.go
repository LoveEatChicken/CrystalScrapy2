package main

import (
	"bytes"
	"commonlib/simplejson"
	"io/ioutil"
	"net/http"
)

//全局的错误码定义
const (
	RCSystemError = 1
	RCNullData    = 2
)

//全局错误信息
var RCErrorInfo = map[int]string{
	RCNullData:    "数据不存在",
	RCSystemError: "系统错误",
}

//---------------------------- 定义通用请求和响应 ----------------------------
//机器人通用请求体
type RobotRequest struct {
	LogId     string //全局日志ID
	UserId    string //全局用户ID
	Query     string //用户query
	Timestamp int64  //收到请求时的时间戳(秒)
}

/**
 *	请求图灵机器人
 *
 */
func ChatQueryProc(req *RobotRequest) (*simplejson.Json, int, error) {
	//构造请求json体
	jreq := simplejson.New()
	jreq.Set("key", Psvr.TLApiKey)
	jreq.Set("info", req.Query)
	jreq.Set("userid", req.UserId)
	content, err := jreq.Encode()
	if err != nil {
		return nil, RCSystemError, err
	}

	bodies := bytes.NewBuffer(content)
	httpReq, err := http.NewRequest("POST", Psvr.TLApiUrl, bodies)
	if err != nil {
		Psvr.Llog.Error("build request failed, what = %s", err.Error())
		return nil, RCNullData, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpResp, err := Psvr.TLHttpClient.Do(httpReq)
	if err != nil {
		Psvr.Llog.Error("query response failed, what = %s", err.Error())
		return nil, RCNullData, err
	}
	if httpResp.StatusCode != http.StatusOK {
		Psvr.Llog.Error("get response failed, http code=%d", httpResp.StatusCode)
		return nil, RCNullData, err
	}
	defer httpResp.Body.Close()
	data, err := ioutil.ReadAll(httpResp.Body)
	if err != nil {
		Psvr.Llog.Error("retrive response failed, what = %s", err.Error())
		return nil, RCNullData, err
	}
	//解析返回的数据为json
	jresp, err := simplejson.NewJson(data)
	if err != nil {
		Psvr.Llog.Error("retrive response failed, what = %s", err.Error())
		return nil, RCNullData, err
	}
	Psvr.Llog.Debug("Tuling Data : %s", string(data))
	return jresp, 0, nil
}
