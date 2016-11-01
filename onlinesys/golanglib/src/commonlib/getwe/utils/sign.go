package utils

import (
	"crypto/md5"
	"fmt"
	"strconv"
)

func StringSignInt32(str string) (uint32, error) {
	buf := md5.Sum([]byte(str))
	return MD5SignInt32(fmt.Sprintf("%x", buf))
}

func MD5SignInt32(md5Str string) (uint32, error) {
	if len(md5Str) != 32 {
		return 0, ErrFmt("%s is not md5 str", md5Str)
	}
	id1, err := strconv.ParseUint(md5Str[0:8], 16, 32)
	if err != nil {
		return 0, err
	}
	id2, err := strconv.ParseUint(md5Str[8:16], 16, 32)
	if err != nil {
		return 0, err
	}
	id3, err := strconv.ParseUint(md5Str[16:24], 16, 32)
	if err != nil {
		return 0, err
	}
	id4, err := strconv.ParseUint(md5Str[24:32], 16, 32)
	if err != nil {
		return 0, err
	}

	return uint32(id1 + id2 + id3 + id4), nil
}
