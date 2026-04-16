// GO VC-4: Service Discovery
// mDNS and Consul integration for mesh node discovery

package discovery

import (
	"context"
	"fmt"
	"log"

	"github.com/hashicorp/consul/api"
)

// ServiceRegistry handles service registration and discovery
type ServiceRegistry struct {
	client    *api.Client
	serviceID string
	addr      string
	port      int
}

// NewServiceRegistry creates a new service registry
func NewServiceRegistry(addr string, port int) (*ServiceRegistry, error) {
	config := api.DefaultConfig()
	client, err := api.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create consul client: %w", err)
	}

	return &ServiceRegistry{
		client:    client,
		serviceID: fmt.Sprintf("whitemagic-%s-%d", addr, port),
		addr:      addr,
		port:      port,
	}, nil
}

// Register registers the service with the discovery backend
func (r *ServiceRegistry) Register(ctx context.Context) error {
	service := &api.AgentServiceRegistration{
		ID:      r.serviceID,
		Name:    "whitemagic",
		Tags:    []string{"mesh", "v17"},
		Port:    r.port,
		Address: r.addr,
		Check: &api.AgentServiceCheck{
			Interval:                       "10s",
			Timeout:                        "5s",
			DeregisterCriticalServiceAfter: "30s",
		},
	}

	if err := r.client.Agent().ServiceRegister(service); err != nil {
		return fmt.Errorf("failed to register service: %w", err)
	}

	log.Printf("Service registered: %s", r.serviceID)
	return nil
}

// Discover finds other whitemagic services
func (r *ServiceRegistry) Discover(ctx context.Context) ([]*api.ServiceEntry, error) {
	services, _, err := r.client.Health().Service("whitemagic", "", true, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to discover services: %w", err)
	}
	return services, nil
}

// Deregister removes the service from discovery
func (r *ServiceRegistry) Deregister(ctx context.Context) error {
	if err := r.client.Agent().ServiceDeregister(r.serviceID); err != nil {
		return fmt.Errorf("failed to deregister service: %w", err)
	}
	return nil
}
