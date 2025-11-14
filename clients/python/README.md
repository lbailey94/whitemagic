# whitemagic-client

Official Python SDK for WhiteMagic.

## Installation
```bash
pip install whitemagic-client
```

## Usage
```python
from whitemagic_client import WhiteMagicClient

client = WhiteMagicClient(api_key='your-key')
memory = client.create_memory({
    'title': 'Test',
    'content': 'Hello',
    'type': 'short_term'
})
```

See full docs at https://github.com/lbailey94/whitemagic
