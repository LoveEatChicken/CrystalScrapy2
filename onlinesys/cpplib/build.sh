#!/usr/bin/env bash

CURR=`cd $(dirname $0)/;pwd`

echo "build scws"
SCWS="$CURR/src/scws-1.2.1/"

# 打补丁,修复会coredump的问题
# 已经直接在代码打了补丁
#sed -ie 's/ifdef HAVE_STRNDUP/ifdef HAVE_STRNDUP_NO_USE_THIS_MACRO/' "$SCWS/libscws/xdb.c"
#sed -ie 's/ifdef HAVE_STRNDUP/ifdef HAVE_STRNDUP_NO_USE_THIS_MACRO/' "$SCWS/libscws/scws.c"

cd "$SCWS"
./configure --prefix="$CURR/usr" && make install

echo "build scws finish"
