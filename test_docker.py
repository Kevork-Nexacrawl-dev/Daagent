from tools.native.execute_docker import execute_docker

# Test Docker ps (list containers)
result = execute_docker('ps')
print("Docker ps result:", result)