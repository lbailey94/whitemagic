import asyncio
from whitemagic.security.sandbox import get_sandbox

async def main():
    print("Testing WhiteMagic Adaptive Sandbox...")
    sandbox = get_sandbox()
    
    # Test 1: Basic Math
    code1 = "print('Hello from the Alpine Sandbox!')\\nprint({'x': 5 * 5})"
    print(f"\\n[Test 1] Executing Basic Code:\\n{code1}")
    result1 = await sandbox.execute_python(code1, timeout_sec=20.0)
    print(f"Stdout:\\n{result1.stdout}\\nStderr: {result1.stderr}\\nExit_Code: {result1.exit_code}\\nTime: {result1.execution_time_ms:.2f}ms")
    
    # Test 2: Timeout limitation
    code2 = "import time\\nwhile True:\\n    time.sleep(1)"
    print(f"\\n[Test 2] Executing Infinite Loop (Should kill gracefully):\\n{code2}")
    result2 = await sandbox.execute_python(code2, timeout_sec=2.0)
    print(f"Result: {result2.stderr}\\nTimeout bool: {result2.timeout}")
    
    # Test 3: System / Disk escape
    code3 = "import os\\ntry:\\n    with open('/etc/shadow', 'r') as f:\\n        print(f.read()[:50])\\nexcept Exception as e:\\n    print('Access denied:', e)"
    print(f"\\n[Test 3] Testing OS File Access:\\n{code3}")
    result3 = await sandbox.execute_python(code3)
    print(f"Stdout:\\n{result3.stdout}\\nStderr: {result3.stderr}\\nExit_Code: {result3.exit_code}")

if __name__ == "__main__":
    asyncio.run(main())
