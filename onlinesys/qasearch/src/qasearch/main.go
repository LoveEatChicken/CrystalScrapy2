package main

import (
	"commonlib/getwe/utils"
	"commonlib/goose"
)

func main() {
	defer utils.CoreDumpExit()

	app := goose.NewGoose()
	app.SetIndexStrategy(new(StyIndexer))
	app.SetSearchStrategy(new(StySearcher))
	app.Run()
}
