#!/usr/bin/env bash

if [ x"$#" == x"0" ];then
    echo "Usage : $0 program"
    exit
fi

PROGRAM=$1
shift

RUN_PATH=`cd $(dirname $0)/..;pwd`
export RUN_PATH
echo "program home : $RUN_PATH"

mkdir -p "$RUN_PATH/tmp"
mkdir -p "$RUN_PATH/log"
mkdir -p "$RUN_PATH/data"
mkdir -p "$RUN_PATH/status"

if [ ! -f "${RUN_PATH}/conf/${PROGRAM}.conf" ];then
    echo "not found conf : ${RUN_PATH}/conf/${PROGRAM}.conf"
    exit
fi

python "$RUN_PATH/bin/main.py" \
    --conf "$RUN_PATH/conf/${PROGRAM}.conf"
