#!/usr/bin/env bash

# go编译需要环境变量
export TMPDIR="/tmp"


CURR=`cd $(dirname $0)/;pwd`
GOLANGLIB=`cd ${CURR}/../golanglib/;pwd`;cd ${CURR}

export GOPATH="${CURR}:${GOLANGLIB}"

