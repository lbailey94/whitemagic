# Gana: gana_roof

**20 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [llama.agent](../tools/llama.agent.md) | inference | write | Run an agentic loop with a local llama.cpp model that can autonomously call Whit |
| [llama.chat](../tools/llama.chat.md) | inference | read | Chat with a local llama.cpp model using message history. Supports context inject |
| [llama.generate](../tools/llama.generate.md) | inference | read | Generate text with a local llama.cpp model. Supports context injection from Whit |
| [llama.models](../tools/llama.models.md) | inference | read | List available models on the local llama-server. |
| [mandala.create](../tools/mandala.create.md) | system | write | Create a new mandala compartment from a template or explicit config (MandalaOS P |
| [mandala.destroy](../tools/mandala.destroy.md) | system | delete | Destroy a mandala compartment and clean up resources (MandalaOS Phase B). Remove |
| [mandala.status](../tools/mandala.status.md) | system | read | List active mandala compartments and available templates (MandalaOS Phase B). Sh |
| [mandala.templates](../tools/mandala.templates.md) | system | read | List available mandala templates with their capabilities, limits, and Dharma pro |
| [model.hash](../tools/model.hash.md) | security | read | Compute SHA-256 hash of a model file |
| [model.list](../tools/model.list.md) | security | read | List all registered model manifests |
| [model.register](../tools/model.register.md) | security | write | Register a model manifest for OpenSSF Model Signing verification |
| [model.signing_status](../tools/model.signing_status.md) | security | read | Return model signing subsystem status |
| [model.verify](../tools/model.verify.md) | security | read | Verify a model against its registered manifest |
| [shelter.create](../tools/shelter.create.md) | system | read | Dispatch-routable WhiteMagic tool 'shelter.create'. |
| [shelter.destroy](../tools/shelter.destroy.md) | system | read | Dispatch-routable WhiteMagic tool 'shelter.destroy'. |
| [shelter.execute](../tools/shelter.execute.md) | system | read | Dispatch-routable WhiteMagic tool 'shelter.execute'. |
| [shelter.inspect](../tools/shelter.inspect.md) | system | read | Dispatch-routable WhiteMagic tool 'shelter.inspect'. |
| [shelter.policy](../tools/shelter.policy.md) | system | read | Dispatch-routable WhiteMagic tool 'shelter.policy'. |
| [shelter.status](../tools/shelter.status.md) | system | read | Dispatch-routable WhiteMagic tool 'shelter.status'. |
| [zodiac.status](../tools/zodiac.status.md) | system | read | Dispatch-routable WhiteMagic tool 'zodiac.status'. |
