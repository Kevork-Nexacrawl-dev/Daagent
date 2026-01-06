from tools.native.execute_python import execute_python
import json

code = "print('héllo wörld 🌍\\n\\t\\r')"
result = execute_python(code)
data = json.loads(result)
print("Status:", data["status"])
print("Stdout:", repr(data["stdout"]))
print("Stderr:", repr(data["stderr"]))
print("Return code:", data["returncode"])