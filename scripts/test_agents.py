#!/usr/bin/env python3
"""
Test script to verify Student and Expert agents work with Together.ai.
Tests actual moderation logic with a sample comment.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.student import StudentAgent
from src.agents.expert import ExpertAgent
from src.agents.base import ModerationRequest


def test_agents():
    """Test Student and Expert agents with Together.ai."""

    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ ERROR: TOGETHER_API_KEY environment variable not set!")
        print("   Set it with: export TOGETHER_API_KEY='your-key-here'")
        return False

    print("🔑 API Key found")
    print()

    # Configure agents
    student_config = {
        "backend": "together",
        "model": "Qwen/Qwen2.5-7B-Instruct-Turbo",
        "max_tokens": 256,
        "temperature": 0.4,
    }

    expert_config = {
        "backend": "together",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "max_tokens": 512,
        "temperature": 0.2,
    }

    print("📚 Initializing Student agent...")
    try:
        student = StudentAgent(student_config)
        print("   ✅ Student agent initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize Student: {str(e)}")
        return False

    print("🎓 Initializing Expert agent...")
    try:
        expert = ExpertAgent(expert_config)
        print("   ✅ Expert agent initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize Expert: {str(e)}")
        return False

    print()

    # Test with a sample comment
    test_comment = "go kys lol"
    print(f"🧪 Testing with comment: '{test_comment}'")
    print()

    req = ModerationRequest(
        comment=test_comment,
        meta={"user": "test_user"},
        persona="firm_professional",
        retrieved=None,
    )

    # Test Student
    print("📚 Student agent moderation...")
    try:
        student_output = student.moderate(req)
        print(f"   Reasoning: {student_output.reasoning[:150]}...")
        print(f"   Plan: {student_output.plan}")
        print(f"   Actions: {student_output.actions}")
        print(f"   Safety Level: {student_output.safety_level}")
        print("   ✅ Student agent works!")
    except Exception as e:
        print(f"   ❌ Student agent failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # Test Expert
    print("🎓 Expert agent moderation...")
    try:
        expert_output = expert.moderate(req)
        print(f"   Reasoning: {expert_output.reasoning[:150]}...")
        print(f"   Plan: {expert_output.plan}")
        print(f"   Actions: {expert_output.actions}")
        print(f"   Safety Level: {expert_output.safety_level}")
        print("   ✅ Expert agent works!")
    except Exception as e:
        print(f"   ❌ Expert agent failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("✅ All agent tests passed! Your setup is working correctly.")
    print()
    print("You can now run the full moderation loop:")
    print("   python scripts/run_loop.py --config configs/default.yaml")

    return True


if __name__ == "__main__":
    success = test_agents()
    sys.exit(0 if success else 1)
