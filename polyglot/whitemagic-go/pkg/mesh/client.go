package mesh

import (
    "context"
    "fmt"
    "log"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
)

// MeshClient provides gRPC connectivity to the mesh
type MeshClient struct {
    conn   *grpc.ClientConn
    client MeshServiceClient
    addr   string
}

// NewMeshClient creates a new mesh client
func NewMeshClient(addr string) (*MeshClient, error) {
    conn, err := grpc.Dial(
        addr,
        grpc.WithTransportCredentials(insecure.NewCredentials()),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to connect: %w", err)
    }

    return &MeshClient{
        conn:   conn,
        client: NewMeshServiceClient(conn),
        addr:   addr,
    }, nil
}

// SendMessage sends a message to the mesh
func (c *MeshClient) SendMessage(ctx context.Context, msg *Message) (*Ack, error) {
    return c.client.SendMessage(ctx, msg)
}

// Close closes the client connection
func (c *MeshClient) Close() error {
    return c.conn.Close()
}
