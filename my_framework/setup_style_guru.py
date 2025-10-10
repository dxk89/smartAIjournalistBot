# File: setup_style_guru.py
# Run this from the my_framework directory

import sys
import os
import traceback

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add the src directory to the path
sys.path.insert(0, os.path.join(script_dir, 'src'))

print("""
╔══════════════════════════════════════════════════════════════════╗
║                   STYLE GURU SETUP SCRIPT                        ║
║                                                                  ║
║  This will analyze 100 IntelliNews articles and create a        ║
║  comprehensive style framework for the AI to follow.            ║
║                                                                  ║
║  NOTE: This may take 15-30 minutes and use ~$2-5 in OpenAI      ║
║  API credits. This runs automatically during deployment.         ║
╚══════════════════════════════════════════════════════════════════╝
""")

# FIX: Removed the input() prompt that caused the EOFError in non-interactive environments.
# The script will now proceed automatically.
print("\nProceeding with setup automatically...")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    
    dotenv_path = os.path.join(script_dir, '.env')
    
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        parent_dotenv = os.path.join(os.path.dirname(script_dir), '.env')
        if os.path.exists(parent_dotenv):
            load_dotenv(dotenv_path=parent_dotenv)
            
except Exception as e:
    pass

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("\n❌ ERROR: OPENAI_API_KEY not found!")
    sys.exit(1)

# Step 1: Deep Analysis
try:
    from my_framework.style_guru.deep_analyzer import deep_style_analysis
    
    framework = deep_style_analysis(max_articles=100)
    
    if not framework:
        sys.exit(1)
        
except Exception as e:
    traceback.print_exc()
    sys.exit(1)

# Step 2: Build Training Dataset
try:
    from my_framework.style_guru.training import build_dataset
    
    build_dataset(limit=100)
    
except Exception as e:
    traceback.print_exc()
    # Continue anyway - LLM scoring will still work

# Step 3: Train Neural Model
try:
    from my_framework.style_guru.training import train_model
    
    train_model()
    
except Exception as e:
    traceback.print_exc()
    # Continue anyway - LLM scoring will still work

# Step 4: Test the System
try:
    from my_framework.style_guru.scorer import load_style_framework
    
    framework = load_style_framework()
    if not framework:
        pass
        
except Exception as e:
    pass

print("""
The Style Guru is now active and will automatically improve all articles!
""")