// Phase 9 Mesh: Node 59
package mesh

import (
    "context"
    "log"
    "net"
    "github.com/gorilla/websocket"
)

type DistributedNode struct {
    ID      string
    Addr    string
    Peers   []string
}

func (n *DistributedNode) Start() error {
    log.Printf("Starting node %s on %s", n.ID, n.Addr)
    return nil
}
