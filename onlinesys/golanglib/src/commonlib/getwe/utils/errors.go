package utils

import (
	"errors"
	"fmt"
)

func ErrFmt(fmtstr string, args ...interface{}) error {
	return errors.New(fmt.Sprintf(fmtstr, args...))
}
