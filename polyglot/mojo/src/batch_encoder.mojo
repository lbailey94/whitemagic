"""Batch Encoder - Mojo 0.26.1 JSON Bridge"""
from python import Python

fn main() raises:
    var py_json = Python.import_module("json")
    var py_sys = Python.import_module("sys")
    
    var input_str = String(py_sys.stdin.read())
    var request = py_json.loads(input_str)
    
    # Get command from request dict
    var cmd_obj = request.get("command")
    var command = String(cmd_obj) if cmd_obj else "unknown"
    
    if command == "batch_encode":
        var result = Python.dict()
        result["coordinates"] = Python.list()
        result["status"] = "ok"
        print(py_json.dumps(result))
    else:
        var error = Python.dict()
        error["error"] = "Unknown command"
        print(py_json.dumps(error))
