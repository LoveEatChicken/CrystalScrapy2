#!/usr/bin/env bash

export PATH="$HOME/.local/bin:$PATH"

command -v pip >/dev/null 2>&1 || {
    echo "Command not found : pip"
    echo "Please install pip"
    exit 1
}


CURR=`cd $(dirname $0)/;pwd`
#export GOPATH="$CURR/"

if [ ! -d "$CURR/pythonlib" ];then
    set -x
    pip install argparse -t "$CURR/pythonlib"
    set +x
fi


# 结果打包
cd "$CURR"
set -x
rm -rf output
mkdir -p output/bin
mkdir -p output/conf
mkdir -p output/log

cp bin/* output/bin
cp conf/* output/conf
cp -r pythonlib output/

chmod +x output/bin/run.sh

set +x
