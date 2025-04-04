from locust import HttpUser, task, between
import random
import string

class MCPUser(HttpUser):
    wait_time = between(1, 5)  # Wait between 1 and 5 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.tools = []
        self.register_tool()
    
    def generate_random_string(self, length: int = 1000) -> str:
        """Generate a random string of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def register_tool(self):
        """Register a new tool."""
        tool_name = f"load_test_tool_{random.randint(1, 1000)}"
        response = self.client.post(
            "/api/v1/tools/register",
            json={
                "name": tool_name,
                "description": "Load test tool",
                "endpoint": "http://localhost:7444/api/v1/llm/generate"
            }
        )
        if response.status_code == 200:
            self.tools.append(tool_name)
    
    @task(3)
    def health_check(self):
        """Check system health."""
        self.client.get("/health")
    
    @task(2)
    def tool_execution(self):
        """Execute a registered tool."""
        if self.tools:
            tool = random.choice(self.tools)
            self.client.post(
                "/api/v1/tools/execute",
                json={
                    "tool": tool,
                    "params": {
                        "prompt": self.generate_random_string(100),
                        "max_tokens": 10
                    }
                }
            )
    
    @task(1)
    def file_operation(self):
        """Perform file operation."""
        self.client.post(
            "/api/v1/local/file_info",
            json={
                "path": "README.md"
            }
        )
    
    @task(1)
    def system_info(self):
        """Get system information."""
        self.client.post(
            "/api/v1/operations/system_info",
            json={}
        )
    
    @task(1)
    def stress_test(self):
        """Perform stress test with large payload."""
        large_payload = self.generate_random_string(10000)
        self.client.post(
            "/api/v1/tools/register",
            json={
                "name": f"stress_tool_{random.randint(1, 1000)}",
                "description": "Stress test tool",
                "endpoint": "http://localhost:7444/api/v1/llm/generate",
                "payload": large_payload
            }
        ) 