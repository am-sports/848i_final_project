#!/usr/bin/env python3
"""
Quick test script to verify Together.ai API token works.
Tests both Student and Expert models with one call each.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
import json


def test_together_api():
    """Test Together.ai API with Student and Expert models."""
    
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ ERROR: TOGETHER_API_KEY environment variable not set!")
        print("   Set it with: export TOGETHER_API_KEY='your-key-here'")
        return False
    
    print("🔑 API Key found")
    print(f"   Key starts with: {api_key[:10]}...")
    print()
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.together.xyz/v1",
    )
    
    # Test Student model
    print("📚 Testing Student model (Qwen/Qwen2.5-7B-Instruct-Turbo)...")
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct-Turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, Student model works!' in JSON format: {\"message\": \"your response\"}"}
            ],
            max_tokens=50,
            temperature=0.4,
        )
        content = response.choices[0].message.content
        print(f"   ✅ Student model response: {content[:100]}...")
        print()
    except Exception as e:
        print(f"   ❌ Student model failed: {str(e)}")
        return False
    
    # Test Expert model
    print("🎓 Testing Expert model (meta-llama/Llama-3.3-70B-Instruct-Turbo)...")
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, Expert model works!' in JSON format: {\"message\": \"your response\"}"}
            ],
            max_tokens=50,
            temperature=0.2,
        )
        content = response.choices[0].message.content
        print(f"   ✅ Expert model response: {content[:100]}...")
        print()
    except Exception as e:
        print(f"   ❌ Expert model failed: {str(e)}")
        return False
    
    print("✅ All tests passed! Your Together.ai API token is working correctly.")
    return True


if __name__ == "__main__":
    success = test_together_api()
    sys.exit(0 if success else 1)

