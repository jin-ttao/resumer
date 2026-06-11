package main

import (
	"os"

	"github.com/jin-ttao/resumer/internal/cli"
)

// version is injected at release time via -ldflags "-X main.version=...".
var version = "dev"

func main() {
	os.Exit(cli.Run(os.Args[1:], version))
}
