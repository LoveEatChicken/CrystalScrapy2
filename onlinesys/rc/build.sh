#!/usr/bin/env bash


PROGRAM="rc"

#====================================

export PATH="$HOME/.local/bin:$PATH"

command -v go>/dev/null 2>&1 || {
    echo "Command not found : go"
    echo "Please install golang dev env"
    exit 1
}

command -v pip >/dev/null 2>&1 || {
    echo "Command not found : pip"
    echo "Please install pip"
    exit 1
}

CURR=`cd $(dirname $0)/;pwd`

if [ ! -d "${CURR}/pythonlib" ];then
    set -x
    pip install setuptools -t "${CURR}/pythonlib"
    pip install supervisor -t "${CURR}/pythonlib"
    touch "${CURR}/pythonlib/supervisor/__init__.py"
    set +x
fi

# golanglib先build一次，必要去编译依赖会先安装
cd ${CURR}/
cd ../golanglib
sh build.sh

# 修改GOPATH环境变量
cd ${CURR};source ${CURR}/GOPATH.sh

# 编译搜索策略算法
cd "${CURR}/src/${PROGRAM}" && go install

exit 0
# 结果打包
cd "${CURR}"
set -x
rm -rf output
OUTPUT="output/${PROGRAM}"
mkdir -p ${OUTPUT}/bin
mkdir -p ${OUTPUT}/dict
mkdir -p ${OUTPUT}/conf
mkdir -p ${OUTPUT}/log
mkdir -p ${OUTPUT}/data

cp bin/${PROGRAM} ${OUTPUT}/bin
cp bin/${PROGRAM}_control ${OUTPUT}/bin
cp bin/supervisord ${OUTPUT}/bin
cp bin/supervisorctl ${OUTPUT}/bin
cp bin/supervisord.conf ${OUTPUT}/bin
cp dict/* ${OUTPUT}/dict
cp conf/* ${OUTPUT}/conf
cp -r pythonlib ${OUTPUT}/

chmod +x ${OUTPUT}/bin/${PROGRAM}
chmod +x ${OUTPUT}/bin/${PROGRAM}_control
chmod +x ${OUTPUT}/bin/supervisord
chmod +x ${OUTPUT}/bin/supervisorctl
set +x
