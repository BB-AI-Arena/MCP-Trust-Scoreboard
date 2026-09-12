// Benign CI helper only. Never packaged with the sensor release artifact.
package main

import (
	"fmt"
	"net"
	"os"
	"time"
)

func main() {
	if len(os.Args) != 2 {
		os.Exit(2)
	}
	c, e := net.DialTimeout("tcp", os.Args[1], 5*time.Second)
	if e != nil {
		os.Exit(3)
	}
	defer c.Close()
	fmt.Fprint(c, "benign sensor fixture\n")
	time.Sleep(90 * time.Second)
}
