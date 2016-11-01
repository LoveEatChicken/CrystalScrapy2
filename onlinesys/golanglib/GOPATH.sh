#!/usr/bin/env bash

# go编译需要环境变量
export TMPDIR="/tmp"


CURR=`cd $(dirname $0)/;pwd`

export GOPATH="${CURR}"

