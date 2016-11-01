package utils

import (
	"bufio"
	"os"
)

type FileIter struct {
	s *bufio.Scanner
}

// 内部进行了一次拷贝返回string
func (this *FileIter) NextDoc() interface{} {
	if this.s.Scan() {
		return this.s.Text()
	}
	return nil
}

func NewFileIter(fh *os.File) *FileIter {
	fi := FileIter{}
	fi.s = bufio.NewScanner(fh)
	return &fi
}

/*
// 把一块buf当成一个doc一次返回
type BufferIterOnce struct {
	buf []byte
}

func (this *BufferIterOnce) NextDoc() interface{} {
	if this.buf != nil {
		tmp := this.buf
		this.buf = nil
		return tmp
	}
	return nil
}

func NewBufferIterOnce(buf []byte) *BufferIterOnce {
	bi := BufferIterOnce{}
	bi.buf = buf
	return &bi
}
*/

type StringIterOnce struct {
	buf string
}

func (this *StringIterOnce) NextDoc() interface{} {
	if this.buf != "" {
		tmp := this.buf
		this.buf = ""
		return tmp
	}
	return nil
}

func NewStringIterOnce(str string) *StringIterOnce {
	si := new(StringIterOnce)
	si.buf = str
	return si
}
