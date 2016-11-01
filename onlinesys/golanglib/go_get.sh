#!/usr/bin/env bash

export PATH="$HOME/.local/bin:$PATH"

command -v go>/dev/null 2>&1 || {
    echo "Command not found : go"
    echo "Please install golang dev env"
    exit 1
}

CURR=`cd $(dirname $0)/;pwd`

# 修改GOPATH环境变量
cd ${CURR};source ${CURR}/GOPATH.sh

# go编译需要环境变量
export TMPDIR="/tmp"

module=$1
# 安装go所需要的开发依赖
echo "Install golang dependence"
set -x
go get "${module}"
set +x
echo "Install golang dependence finish"
