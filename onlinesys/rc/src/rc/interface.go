package main

import (
	//"gopkg.in/mgo.v2"
	//"gopkg.in/mgo.v2/bson"
	"commonlib/simplejson"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
)

//全局的错误码定义
const (
	RCRequestFmtError    = 41001
	RCAuthorLimited      = 41002
	RCMethodNotSupported = 40003
	RCNullData           = 40004
	RCSystemError        = 41005
)

//全局错误信息
var RCErrorInfo = map[int]string{
	RCAuthorLimited:      "无权操作",
	RCMethodNotSupported: "请求方法不支持",
	RCRequestFmtError:    "请求参数格式错误",
	RCNullData:           "数据不存在",
	RCSystemError:        "系统错误",
}

//---------------------------- 定义通用请求和响应 ----------------------------
//判断为http post json，出错则直接返回http 400、405、500
func parsePostRequest(w *http.ResponseWriter, r *http.Request) (*simplejson.Json, error) {
	if r.Method != "POST" {
		http.Error(*w, "Method need post", http.StatusMethodNotAllowed)
		return nil, fmt.Errorf("Method need post")
	}
	//解析包体
	str_req, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(*w, "Recv request body failed.", http.StatusInternalServerError)
		return nil, fmt.Errorf("Recv request body failed.")
	}
	Psvr.Llog.Debug("Detail request : %s", string(str_req))

	js, err := simplejson.NewJson(str_req)
	if err != nil {
		http.Error(*w, "Badrequest not json.", http.StatusBadRequest)
		return nil, fmt.Errorf("Badrequest not json.")
	}

	//设置响应报为json
	(*w).Header().Add("Content-Type", "application/json")
	return js, nil
}

//出错响应
func errJsonResp(code int) string {
	return fmt.Sprintf("{\"error\":\"%d\",\"msg\":\"%s\",\"content\":\"%s\"}", code,
		RCErrorInfo[code], RCErrorInfo[code])
}

//返回正常响应字符串
func okJsonResp(data *simplejson.Json) string {
	resp := simplejson.New() //新建一个空的json
	resp.Set("error", "0")
	resp.Set("content", data)

	str_buf, err := resp.MarshalJSON()
	if err != nil {
		return errJsonResp(RCSystemError)
	}
	return string(str_buf)
}

//---------------------------- 定义所有对外服务接口 ----------------------------
//interface中将请求解析为json格式，传递到业务函数中处理
//业务函数统一返回一个json，写回w
//注意：只接受post请求

//for test hello
func helloHandler(w http.ResponseWriter, r *http.Request) {
	//Psvr.Llog.Debug("Reveiver a request in /hello.")
	io.WriteString(w, "{\"hello\":\"world\"}")
}

//for query
func queryHandler(w http.ResponseWriter, r *http.Request) {
	Psvr.Llog.Debug("Reveiver a request in /ai/query.")
	js, err := parsePostRequest(&w, r)
	if err != nil {
		//报错直接返回即可
		return
	}

	//调用逻辑处理
	jresp, retcode, err := AIQueryProc(js, 0)
	if err != nil {
		//错误返回
		io.WriteString(w, errJsonResp(retcode))
		Psvr.Llog.Error(err.Error())
		return
	}

	//正常返回
	io.WriteString(w, okJsonResp(jresp))
}

//for query
func whiteBoardHandler(w http.ResponseWriter, r *http.Request) {
	Psvr.Llog.Debug("Reveiver a request in /ai/query.")
	js, err := parsePostRequest(&w, r)
	if err != nil {
		//报错直接返回即可
		return
	}

	//调用逻辑处理
	jresp, retcode, err := AIQueryProc(js, 1)
	if err != nil {
		//错误返回
		io.WriteString(w, errJsonResp(retcode))
		Psvr.Llog.Error(err.Error())
		return
	}

	//正常返回
	io.WriteString(w, okJsonResp(jresp))
}
