import whitemagic_rust

print("IPC Bridge Available:", hasattr(whitemagic_rust, 'ipc_bridge'))
if hasattr(whitemagic_rust, 'ipc_bridge'):
    print("Methods:", dir(whitemagic_rust.ipc_bridge))

    try:
        # We may need root/special permissions or a specific environment for true iceoryx2,
        # but let's see what happens when we call init and status.
        status = whitemagic_rust.ipc_bridge.ipc_status()
        print("Initial Status:", status)
    except Exception as e:
        print("Status error:", e)
