#!/usr/bin/bash

command -v protoc>/dev/null 2>&1 || {
    echo "Command not found : protoc"
    echo "Please install protoc"
    echo "http://www.grpc.io/docs/quickstart/go.html#install-protocol-buffers-v3"
    exit 1
}

# golang rpc implement 
golanglib="../../golanglib"
gorpcimp="${golanglib}/src/gorpcimp"

mkdir -p ${gorpcimp}/bot
mkdir -p ${gorpcimp}/qu
mkdir -p ${gorpcimp}/session
mkdir -p ${gorpcimp}/search

set -x

# qu server idl imp
protoc -I . ./qu_server.proto --go_out=plugins=grpc:${gorpcimp}/qu

# session server idl imp
protoc -I . ./session_server.proto --go_out=plugins=grpc:${gorpcimp}/session

protoc -I . ./bot.proto --go_out=plugins=grpc:${gorpcimp}/bot

protoc -I . ./search.proto --go_out=plugins=grpc:${gorpcimp}/search
