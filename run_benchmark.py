#!/usr/bin/env python3
"""
Quick benchmark runner
"""

import subprocess
import sys
from pathlib import Path

def main():
    script_path = Path(__file__).parent / "benchmark_simple.py"
    
    print("🔧 Starting OpenAI benchmark...")
    print("Make sure you have staged changes in git!\n")
    
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Benchmark failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Benchmark interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()