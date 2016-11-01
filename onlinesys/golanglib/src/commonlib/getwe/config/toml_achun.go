package config

import (
	"fmt"
	"github.com/achun/tom-toml"
)

type TomlConf_achun struct {
	conf toml.Toml
}

func (this *TomlConf_achun) String(key string) string {
	return this.conf[key].String()
}

func (this *TomlConf_achun) StringDefault(key string, d string) string {
	item := this.conf[key]
	if !item.IsValid() {
		return d
	}
	return item.String()
}

func (this *TomlConf_achun) Int64(key string) int64 {
	return this.conf[key].Int()
}

func (this *TomlConf_achun) Float64(key string) float64 {
	return this.conf[key].Float()
}

func (this *TomlConf_achun) Int64Default(key string, d int64) int64 {
	item := this.conf[key]
	if !item.IsValid() {
		return d
	}
	return item.Int()
}

func (this *TomlConf_achun) Bool(key string) bool {
	return this.conf[key].Boolean()
}

func (this *TomlConf_achun) BoolDefault(key string, d bool) bool {
	item := this.conf[key]
	if !item.IsValid() {
		return d
	}
	return item.Boolean()
}

func (this *TomlConf_achun) Float64Array(key string) []float64 {
	return this.conf[key].FloatArray()
}

func (this *TomlConf_achun) StringArray(key string) []string {
	return this.conf[key].StringArray()
}

type tomlConfParser_achun struct {
}

func (this *tomlConfParser_achun) Parse(file string) (c Conf, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("%s", r)
		}
	}()

	tconf := &TomlConf_achun{}
	tconf.conf, err = toml.LoadFile(file)
	if err != nil {
		return nil, err
	}
	return tconf, nil
}

func init() {
	register(".toml", &tomlConfParser_achun{})
}
