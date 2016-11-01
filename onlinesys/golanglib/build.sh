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

# 安装go所需要的开发依赖
# 安装到一个公共目录下
set -x
sh go_get.sh "google.golang.org/grpc"
sh go_get.sh "github.com/golang/protobuf/proto"
sh go_get.sh "github.com/golang/protobuf/protoc-gen-go"

sh go_get.sh "github.com/stretchr/testify/assert"
sh go_get.sh "github.com/jessevdk/go-flags"
set +x

# 编译依赖环境加入本模块自己编译的优先使用
# scws4go需要用到
export C_INCLUDE_PATH="$CURR/../cpplib/usr/include:$C_INCLUDE_PATH"
export CPLUS_INCLUDE_PATH="$C_INCLUDE_PATH"
export LIBRARY_PATH="$CURR/../cpplib/usr/lib:$LIBRARY_PATH"

# 各个模块编译安装一下确认成功
LIBLIST="\
    commonlib/getwe/config \
    commonlib/getwe/go-darts \
    commonlib/scws4go \
    commonlib/getwe/log"

for lib in $LIBLIST; do
    cd "${CURR}/src/${lib}" && go install
done


