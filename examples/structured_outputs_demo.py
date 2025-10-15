#!/usr/bin/env python3
"""
MCP Tools Demo Script - Structured Output Features (2025-06-18)

This script demonstrates the new structured tool output features introduced
in MCP protocol version 2025-06-18, showcasing how tools can return both
traditional text content and structured data.

Features demonstrated:
- Text-only tool results (legacy compatibility)
- Structured-only tool results (new in 2025-06-18)
- Mixed content results (text + structured data)
- Error handling with structured error data
- Tool registry and execution
- JSON schema validation for structured output
- Real-world tool examples

Usage:
    python tools_demo.py
"""

import asyncio
import json
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any

# chuk-mcp imports
from chuk_mcp.protocol.types.tools import (
    Tool,
    ToolInputSchema,
    ToolResult,
    StructuredContent,
    create_text_tool_result,
    create_structured_tool_result,
    create_mixed_tool_result,
    create_error_tool_result,
    validate_tool_result,
    ToolRegistry,
)
from chuk_mcp.protocol.types.content import create_text_content


class DemoToolRegistry(ToolRegistry):
    """
    Extended tool registry with demo tools showcasing structured output.
    """

    def __init__(self):
        super().__init__()
        self._setup_demo_tools()

    def _setup_demo_tools(self):
        """Register all demo tools."""
        # 1. Legacy text-only tool
        self.register_tool(
            Tool(
                name="legacy_greet",
                description="Simple greeting tool (legacy text output)",
                inputSchema=ToolInputSchema(
                    properties={
                        "name": {"type": "string", "description": "Name to greet"}
                    },
                    required=["name"],
                ),
            ),
            self._legacy_greet_handler,
        )

        # 2. Structured data analysis tool
        self.register_tool(
            Tool(
                name="analyze_text",
                description="Analyze text and return structured insights",
                inputSchema=ToolInputSchema(
                    properties={
                        "text": {"type": "string", "description": "Text to analyze"},
                        "include_sentiment": {"type": "boolean", "default": True},
                        "include_keywords": {"type": "boolean", "default": True},
                    },
                    required=["text"],
                ),
            ),
            self._analyze_text_handler,
        )

        # 3. Weather data tool (mixed content)
        self.register_tool(
            Tool(
                name="get_weather",
                description="Get weather data with both summary and detailed metrics",
                inputSchema=ToolInputSchema(
                    properties={
                        "location": {"type": "string", "description": "Location name"},
                        "units": {
                            "type": "string",
                            "enum": ["metric", "imperial"],
                            "default": "metric",
                        },
                    },
                    required=["location"],
                ),
            ),
            self._get_weather_handler,
        )

        # 4. Data processing tool
        self.register_tool(
            Tool(
                name="process_dataset",
                description="Process and analyze a dataset",
                inputSchema=ToolInputSchema(
                    properties={
                        "data": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Numeric data to process",
                        },
                        "operations": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["stats", "outliers", "distribution"],
                            },
                            "description": "Analysis operations to perform",
                        },
                    },
                    required=["data", "operations"],
                ),
            ),
            self._process_dataset_handler,
        )

        # 5. System info tool (structured only)
        self.register_tool(
            Tool(
                name="system_info",
                description="Get system information in structured format",
                inputSchema=ToolInputSchema(
                    properties={"detailed": {"type": "boolean", "default": False}}
                ),
            ),
            self._system_info_handler,
        )

        # 6. Error demonstration tool
        self.register_tool(
            Tool(
                name="demo_error",
                description="Demonstrate structured error reporting",
                inputSchema=ToolInputSchema(
                    properties={
                        "error_type": {
                            "type": "string",
                            "enum": ["validation", "permission", "network", "internal"],
                            "description": "Type of error to simulate",
                        }
                    },
                    required=["error_type"],
                ),
            ),
            self._demo_error_handler,
        )

    # Tool handlers

    async def _legacy_greet_handler(self, args: Dict[str, Any]) -> ToolResult:
        """Legacy text-only greeting tool."""
        name = args.get("name", "World")
        greeting = f"Hello, {name}! This is a legacy text-only response."

        return create_text_tool_result(greeting)

    async def _analyze_text_handler(self, args: Dict[str, Any]) -> ToolResult:
        """Analyze text and return structured insights."""
        text = args.get("text", "")
        include_sentiment = args.get("include_sentiment", True)
        include_keywords = args.get("include_keywords", True)

        # Simple analysis (in real implementation, use NLP libraries)
        words = text.split()
        sentences = text.split(".")
        characters = len(text)

        # Sentiment analysis (mock)
        sentiment_score = random.uniform(-1, 1)
        sentiment = (
            "positive"
            if sentiment_score > 0.2
            else "negative"
            if sentiment_score < -0.2
            else "neutral"
        )

        # Keywords (mock - just first few words)
        keywords = words[: min(5, len(words))]

        # Build structured data
        analysis_data = {
            "text_length": characters,
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "average_word_length": sum(len(word) for word in words) / len(words)
            if words
            else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if include_sentiment:
            analysis_data.update(
                {
                    "sentiment": {
                        "label": sentiment,
                        "score": round(sentiment_score, 3),
                        "confidence": random.uniform(0.7, 0.95),
                    }
                }
            )

        if include_keywords:
            analysis_data["keywords"] = keywords

        # Create mixed content result
        summary = (
            f"Analyzed text: {len(words)} words, {len(sentences)} sentences. "
            f"Sentiment: {sentiment}"
        )

        return create_mixed_tool_result(
            text_content=[create_text_content(summary)],
            structured_content=[
                StructuredContent(
                    type="structured",
                    data=analysis_data,
                    schema={
                        "type": "object",
                        "properties": {
                            "text_length": {"type": "integer"},
                            "word_count": {"type": "integer"},
                            "sentence_count": {"type": "integer"},
                            "average_word_length": {"type": "number"},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "sentiment": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "score": {
                                        "type": "number",
                                        "minimum": -1,
                                        "maximum": 1,
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                },
                            },
                            "keywords": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    mimeType="application/json",
                )
            ],
        )

    async def _get_weather_handler(self, args: Dict[str, Any]) -> ToolResult:
        """Get weather data with mixed content."""
        location = args.get("location", "Unknown")
        units = args.get("units", "metric")

        # Mock weather data
        temp_celsius = random.uniform(-10, 35)
        temp_fahrenheit = (temp_celsius * 9 / 5) + 32

        display_temp = temp_celsius if units == "metric" else temp_fahrenheit
        temp_unit = "°C" if units == "metric" else "°F"

        weather_data = {
            "location": location,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": {
                "value": round(display_temp, 1),
                "unit": temp_unit,
                "celsius": round(temp_celsius, 1),
                "fahrenheit": round(temp_fahrenheit, 1),
            },
            "humidity": random.randint(30, 90),
            "pressure": round(random.uniform(980, 1030), 1),
            "wind": {
                "speed": round(random.uniform(0, 20), 1),
                "direction": random.choice(
                    ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                ),
            },
            "conditions": random.choice(
                ["sunny", "partly_cloudy", "cloudy", "rainy", "snowy"]
            ),
            "uv_index": random.randint(0, 11),
        }

        # Create weather summary
        summary = (
            f"Weather in {location}: {display_temp}{temp_unit}, "
            f"{weather_data['conditions']}, {weather_data['humidity']}% humidity"
        )

        return create_mixed_tool_result(
            text_content=[create_text_content(summary)],
            structured_content=[
                StructuredContent(
                    type="structured",
                    data=weather_data,
                    schema={
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "temperature": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string"},
                                    "celsius": {"type": "number"},
                                    "fahrenheit": {"type": "number"},
                                },
                            },
                            "humidity": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "pressure": {"type": "number"},
                            "wind": {
                                "type": "object",
                                "properties": {
                                    "speed": {"type": "number"},
                                    "direction": {"type": "string"},
                                },
                            },
                            "conditions": {"type": "string"},
                            "uv_index": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 11,
                            },
                        },
                    },
                    mimeType="application/json",
                )
            ],
        )

    async def _process_dataset_handler(self, args: Dict[str, Any]) -> ToolResult:
        """Process dataset and return detailed analysis."""
        data = args.get("data", [])
        operations = args.get("operations", [])

        if not data:
            return create_error_tool_result("No data provided for processing")

        results = {}

        if "stats" in operations:
            results["statistics"] = {
                "count": len(data),
                "sum": sum(data),
                "mean": sum(data) / len(data),
                "min": min(data),
                "max": max(data),
                "range": max(data) - min(data),
            }

            # Calculate standard deviation
            mean = results["statistics"]["mean"]
            variance = sum((x - mean) ** 2 for x in data) / len(data)
            results["statistics"]["std_dev"] = variance**0.5

        if "outliers" in operations:
            # Simple outlier detection using IQR
            sorted_data = sorted(data)
            n = len(sorted_data)
            q1 = sorted_data[n // 4]
            q3 = sorted_data[3 * n // 4]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = [x for x in data if x < lower_bound or x > upper_bound]

            results["outliers"] = {
                "count": len(outliers),
                "values": outliers,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
            }

        if "distribution" in operations:
            # Simple distribution analysis
            sorted_data = sorted(data)
            n = len(sorted_data)

            results["distribution"] = {
                "median": sorted_data[n // 2],
                "q1": sorted_data[n // 4],
                "q3": sorted_data[3 * n // 4],
                "percentiles": {
                    "p10": sorted_data[int(0.1 * n)],
                    "p25": sorted_data[int(0.25 * n)],
                    "p75": sorted_data[int(0.75 * n)],
                    "p90": sorted_data[int(0.9 * n)],
                },
            }

        # Add metadata
        results["metadata"] = {
            "operations_performed": operations,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "input_size": len(data),
        }

        summary = f"Processed dataset of {len(data)} values with operations: {', '.join(operations)}"

        return create_mixed_tool_result(
            text_content=[create_text_content(summary)],
            structured_content=[
                StructuredContent(
                    type="structured", data=results, mimeType="application/json"
                )
            ],
        )

    async def _system_info_handler(self, args: Dict[str, Any]) -> ToolResult:
        """Get system information (structured only)."""
        detailed = args.get("detailed", False)

        # Mock system info
        system_data = {
            "platform": "demo_system",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": random.randint(3600, 86400),
            "memory": {
                "total_mb": 8192,
                "used_mb": random.randint(2000, 6000),
                "available_mb": None,  # Will be calculated
            },
            "cpu": {"cores": 8, "usage_percent": round(random.uniform(10, 80), 1)},
            "status": "healthy",
        }

        system_data["memory"]["available_mb"] = (
            system_data["memory"]["total_mb"] - system_data["memory"]["used_mb"]
        )

        if detailed:
            system_data.update(
                {
                    "processes": {
                        "total": random.randint(150, 300),
                        "running": random.randint(50, 100),
                        "sleeping": random.randint(80, 180),
                    },
                    "network": {
                        "interfaces": ["eth0", "lo"],
                        "bytes_sent": random.randint(1000000, 10000000),
                        "bytes_received": random.randint(5000000, 50000000),
                    },
                    "disk": {
                        "total_gb": 500,
                        "used_gb": random.randint(100, 400),
                        "free_gb": None,  # Will be calculated
                    },
                }
            )
            system_data["disk"]["free_gb"] = (
                system_data["disk"]["total_gb"] - system_data["disk"]["used_gb"]
            )

        return create_structured_tool_result(
            data=system_data,
            schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "version": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "uptime_seconds": {"type": "integer"},
                    "status": {"type": "string"},
                },
            },
        )

    async def _demo_error_handler(self, args: Dict[str, Any]) -> ToolResult:
        """Demonstrate structured error reporting."""
        error_type = args.get("error_type")

        error_scenarios = {
            "validation": {
                "message": "Input validation failed",
                "data": {
                    "error_code": "VALIDATION_ERROR",
                    "field": "email",
                    "provided_value": "invalid-email",
                    "expected_format": "user@domain.com",
                    "validation_rules": ["required", "email_format"],
                },
            },
            "permission": {
                "message": "Access denied: insufficient permissions",
                "data": {
                    "error_code": "PERMISSION_DENIED",
                    "required_permission": "admin:write",
                    "user_permissions": ["user:read", "user:write"],
                    "resource": "/admin/users",
                    "action": "delete",
                },
            },
            "network": {
                "message": "Network connection failed",
                "data": {
                    "error_code": "NETWORK_ERROR",
                    "host": "api.external-service.com",
                    "port": 443,
                    "timeout_seconds": 30,
                    "retry_count": 3,
                    "last_error": "Connection timeout",
                },
            },
            "internal": {
                "message": "Internal server error occurred",
                "data": {
                    "error_code": "INTERNAL_ERROR",
                    "component": "database_processor",
                    "transaction_id": "tx_" + str(random.randint(100000, 999999)),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": "corr_" + str(random.randint(100000, 999999)),
                },
            },
        }

        scenario = error_scenarios[error_type]

        return create_error_tool_result(
            error_message=scenario["message"], error_data=scenario["data"]
        )


async def demonstrate_tool_features():
    """Demonstrate all tool features with examples."""
    print("🔧 MCP Tools Demo - Structured Output Features (2025-06-18)")
    print("=" * 70)

    # Create demo registry
    registry = DemoToolRegistry()

    print(f"📋 Registered {len(registry.tools)} demo tools:")
    for tool_name, tool in registry.tools.items():
        print(f"   • {tool_name}: {tool.description}")

    print("\n🚀 Running demonstrations...\n")

    # Demo 1: Legacy text-only tool
    print("1️⃣  Legacy Text-Only Tool")
    print("-" * 30)
    result = await registry.call_tool("legacy_greet", {"name": "Alice"})
    print(f"   Text Output: {result.content[0].text}")
    print(f"   Has Structured Data: {result.structuredContent is not None}")
    print(f"   Valid Result: {validate_tool_result(result)}")

    # Demo 2: Text analysis (mixed content)
    print("\n2️⃣  Text Analysis Tool (Mixed Content)")
    print("-" * 45)
    sample_text = "The quick brown fox jumps over the lazy dog. This is a sample text for analysis."
    result = await registry.call_tool(
        "analyze_text",
        {"text": sample_text, "include_sentiment": True, "include_keywords": True},
    )

    print(f"   Text Summary: {result.content[0].text}")
    print("   Structured Data:")
    structured_data = result.structuredContent[0].data
    print(f"      • Words: {structured_data['word_count']}")
    print(f"      • Characters: {structured_data['text_length']}")
    print(
        f"      • Sentiment: {structured_data['sentiment']['label']} ({structured_data['sentiment']['score']:.3f})"
    )
    print(f"      • Keywords: {', '.join(structured_data['keywords'])}")

    # Demo 3: Weather data (mixed content)
    print("\n3️⃣  Weather Data Tool (Mixed Content)")
    print("-" * 42)
    result = await registry.call_tool(
        "get_weather", {"location": "San Francisco", "units": "metric"}
    )

    print(f"   Weather Summary: {result.content[0].text}")
    print("   Detailed Metrics:")
    weather_data = result.structuredContent[0].data
    print(
        f"      • Temperature: {weather_data['temperature']['celsius']}°C / {weather_data['temperature']['fahrenheit']}°F"
    )
    print(f"      • Conditions: {weather_data['conditions']}")
    print(f"      • Humidity: {weather_data['humidity']}%")
    print(
        f"      • Wind: {weather_data['wind']['speed']} km/h {weather_data['wind']['direction']}"
    )
    print(f"      • UV Index: {weather_data['uv_index']}")

    # Demo 4: Dataset processing
    print("\n4️⃣  Dataset Processing Tool")
    print("-" * 32)
    sample_data = [1, 2, 3, 4, 5, 10, 15, 20, 25, 100, 2, 3, 4, 5, 6]
    result = await registry.call_tool(
        "process_dataset",
        {"data": sample_data, "operations": ["stats", "outliers", "distribution"]},
    )

    print(f"   Processing Summary: {result.content[0].text}")
    print("   Statistical Analysis:")
    analysis = result.structuredContent[0].data

    if "statistics" in analysis:
        stats = analysis["statistics"]
        print(f"      • Count: {stats['count']}")
        print(f"      • Mean: {stats['mean']:.2f}")
        print(f"      • Std Dev: {stats['std_dev']:.2f}")
        print(f"      • Range: {stats['min']} - {stats['max']}")

    if "outliers" in analysis:
        outliers = analysis["outliers"]
        print(f"      • Outliers: {outliers['count']} found: {outliers['values']}")

    if "distribution" in analysis:
        dist = analysis["distribution"]
        print(f"      • Median: {dist['median']}")
        print(f"      • IQR: {dist['q1']} - {dist['q3']}")

    # Demo 5: System info (structured only)
    print("\n5️⃣  System Information Tool (Structured Only)")
    print("-" * 50)
    result = await registry.call_tool("system_info", {"detailed": True})

    print("   No text output (structured data only)")
    print("   System Information:")
    sys_data = result.structuredContent[0].data
    print(f"      • Platform: {sys_data['platform']} v{sys_data['version']}")
    print(f"      • Status: {sys_data['status']}")
    print(f"      • Uptime: {sys_data['uptime_seconds']} seconds")
    print(
        f"      • Memory: {sys_data['memory']['used_mb']}/{sys_data['memory']['total_mb']} MB used"
    )
    print(
        f"      • CPU: {sys_data['cpu']['usage_percent']}% usage ({sys_data['cpu']['cores']} cores)"
    )

    if "disk" in sys_data:
        print(
            f"      • Disk: {sys_data['disk']['used_gb']}/{sys_data['disk']['total_gb']} GB used"
        )

    # Demo 6: Error handling with structured data
    print("\n6️⃣  Error Handling with Structured Data")
    print("-" * 44)

    error_types = ["validation", "permission", "network", "internal"]

    for error_type in error_types[:2]:  # Show first 2 for brevity
        result = await registry.call_tool("demo_error", {"error_type": error_type})

        print(f"   {error_type.title()} Error:")
        print(f"      Message: {result.content[0].text}")
        print(f"      Error Code: {result.structuredContent[0].data['error_code']}")

        # Show specific error details
        error_data = result.structuredContent[0].data
        if error_type == "validation":
            print(f"      Field: {error_data['field']}")
            print(f"      Expected: {error_data['expected_format']}")
        elif error_type == "permission":
            print(f"      Required: {error_data['required_permission']}")
            print(f"      User Has: {', '.join(error_data['user_permissions'])}")

    # Demo 7: Schema validation
    print("\n7️⃣  Schema Validation and Serialization")
    print("-" * 44)

    # Get a result with schema
    result = await registry.call_tool(
        "analyze_text", {"text": "Test schema validation"}
    )
    structured = result.structuredContent[0]

    print(f"   Schema Provided: {structured.schema is not None}")
    print(f"   MIME Type: {structured.mimeType}")
    print(f"   Data Type: {type(structured.data).__name__}")

    # Demonstrate serialization
    serialized = json.dumps(structured.data, indent=2)
    print(f"   JSON Size: {len(serialized)} characters")
    print("   Sample JSON:")
    print(
        "   " + serialized[:100] + "..."
        if len(serialized) > 100
        else "   " + serialized
    )

    # Demo 8: Performance comparison
    print("\n8️⃣  Performance Comparison")
    print("-" * 30)

    # Time different tool types
    start_time = time.time()
    for i in range(10):
        await registry.call_tool("legacy_greet", {"name": f"User{i}"})
    legacy_time = time.time() - start_time

    start_time = time.time()
    for i in range(10):
        await registry.call_tool("system_info", {"detailed": False})
    structured_time = time.time() - start_time

    start_time = time.time()
    for i in range(10):
        await registry.call_tool("analyze_text", {"text": f"Sample text {i}"})
    mixed_time = time.time() - start_time

    print(f"   Legacy Tools (10 calls): {legacy_time:.3f}s")
    print(f"   Structured Tools (10 calls): {structured_time:.3f}s")
    print(f"   Mixed Content Tools (10 calls): {mixed_time:.3f}s")

    print("\n🎉 Demo completed successfully!")
    print("\n📊 Summary of Features Demonstrated:")
    print("   ✅ Legacy text-only outputs (backwards compatibility)")
    print("   ✅ Structured data outputs (2025-06-18 feature)")
    print("   ✅ Mixed content outputs (text + structured)")
    print("   ✅ JSON Schema validation for structured data")
    print("   ✅ Error handling with structured error data")
    print("   ✅ MIME type specification for data format")
    print("   ✅ Tool registry and execution management")
    print("   ✅ Real-world tool examples (analysis, weather, data processing)")
    print("   ✅ Performance characteristics across tool types")


async def interactive_tool_explorer():
    """Interactive tool explorer for hands-on testing."""
    print("\n🎮 Interactive Tool Explorer")
    print("=" * 40)
    print("Try running tools interactively!")
    print("Available commands:")
    print("   list - List all available tools")
    print("   info <tool_name> - Get tool information")
    print("   call <tool_name> <json_args> - Call a tool")
    print("   quit - Exit explorer")
    print()

    registry = DemoToolRegistry()

    while True:
        try:
            command = input("🔧 > ").strip()

            if command == "quit":
                break
            elif command == "list":
                print("Available tools:")
                for tool_name, tool in registry.tools.items():
                    print(f"   • {tool_name}: {tool.description}")
            elif command.startswith("info "):
                tool_name = command[5:].strip()
                if tool_name in registry.tools:
                    tool = registry.tools[tool_name]
                    print(f"Tool: {tool.name}")
                    print(f"Description: {tool.description}")
                    print(
                        f"Input Schema: {json.dumps(tool.inputSchema.model_dump(), indent=2)}"
                    )
                else:
                    print(f"Tool '{tool_name}' not found")
            elif command.startswith("call "):
                parts = command[5:].split(" ", 1)
                if len(parts) < 2:
                    print("Usage: call <tool_name> <json_args>")
                    continue

                tool_name, args_str = parts
                try:
                    args = json.loads(args_str)
                    result = await registry.call_tool(tool_name, args)

                    print(f"Result (isError: {result.isError}):")

                    if result.content:
                        print("Text Content:")
                        for content in result.content:
                            print(f"   {content.text}")

                    if result.structuredContent:
                        print("Structured Content:")
                        for structured in result.structuredContent:
                            print(f"   Type: {structured.type}")
                            print(f"   MIME: {structured.mimeType}")
                            print(f"   Data: {json.dumps(structured.data, indent=4)}")

                except json.JSONDecodeError:
                    print("Invalid JSON arguments")
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print("Unknown command. Type 'quit' to exit.")

        except (KeyboardInterrupt, EOFError):
            break

    print("\n👋 Thanks for exploring MCP tools!")


def main():
    """Main entry point."""
    print("🔧 MCP Tools Demo - Structured Output Features")
    print("=" * 60)
    print("Demonstrating the new structured tool output capabilities")
    print("introduced in MCP protocol version 2025-06-18")
    print("=" * 60)

    try:
        # Run main demonstration
        asyncio.run(demonstrate_tool_features())

        # Ask if user wants interactive mode
        print("\n" + "=" * 60)
        response = input("Would you like to try the interactive tool explorer? (y/N): ")

        if response.lower().startswith("y"):
            asyncio.run(interactive_tool_explorer())

        print("\n" + "=" * 60)
        print("🎉 MCP Tools Demo completed!")
        print("\nKey takeaways:")
        print("   📚 Tools can now return structured data alongside text")
        print("   🔍 JSON schemas provide validation and documentation")
        print("   🎯 Mixed content enables rich, contextual responses")
        print("   🚨 Structured error data improves debugging")
        print("   🔄 Full backwards compatibility maintained")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n💥 Demo failed: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
