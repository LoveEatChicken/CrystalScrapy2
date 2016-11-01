# onlinesys

## golanglib
统一管理与业务无关的基础组件库，包括第三方开源模块(github.com)和本地实现的私有模块
业务相关模块不用重复安装依赖，通过软连接使用golanglib的基础组件。

用法参考qu模块的build.sh

## cpplib
cpp的基础库

go语言版的切词程序scws4go只是对scws的一层cgo封装

## qu
query理解模块

## searchkit
检索系统建库、换库等相关辅助程序集合

### indexbuild
通用建库程序，通过配置文件来实现不同的换库逻辑

### indexupdate
通用换库程序，通过配置文件来实现不同的换库逻辑
