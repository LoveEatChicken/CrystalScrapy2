#!/usr/bin/env bash

# go编译需要环境变量
export TMPDIR="/tmp"


CURR=`cd $(dirname $0)/;pwd`
GOLANGLIB=`cd ${CURR}/../golanglib/;pwd`;cd ${CURR}

export GOPATH="${CURR}:${GOLANGLIB}"

# 编译依赖环境加入本模块自己编译的优先使用
# scws4go需要用到
export C_INCLUDE_PATH="$CURR/../cpplib/usr/include:$C_INCLUDE_PATH"
export CPLUS_INCLUDE_PATH="$C_INCLUDE_PATH"
export LIBRARY_PATH="$CURR/../cpplib/usr/lib:$LIBRARY_PATH"


