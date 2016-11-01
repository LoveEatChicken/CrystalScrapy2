#!/usr/bin/env bash

export PATH="$HOME/.local/bin:$PATH"

command -v pip >/dev/null 2>&1 || {
    echo "Command not found : pip"
    echo "Please install pip"
    exit 1
}


CURR=`cd $(dirname $0)/;pwd`

if [ ! -d "$CURR/pythonlib" ];then
    set -x
    pip install mysql-connector-python-rf -t "$CURR/pythonlib"
    set +x
fi


# 结果打包
cd "$CURR"
set -x
rm -rf output
mkdir -p output/indexbuild/bin
mkdir -p output/indexbuild/conf
mkdir -p output/indexbuild/log

cp bin/* output/indexbuild/bin
cp conf/* output/indexbuild/conf
cp -r pythonlib output/indexbuild

chmod +x output/indexbuild/bin/run.sh

set +x
