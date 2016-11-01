package goosesty

import (
	"fmt"
)

const (
	WHOLE_MATCH_PREFIX = "whole"
	FIELD_MATCH_PREFIX = "field"
)

// 创建一个全匹配的term
func GetWholeMatchTerm(term, field string) string {
	return fmt.Sprintf("%s_%s_%s", WHOLE_MATCH_PREFIX, field, term)
}

// 创建一个部分匹配的term
func GetFieldMatchTerm(term, field string) string {
	return fmt.Sprintf("%s_%s_%s", FIELD_MATCH_PREFIX, field, term)
}
