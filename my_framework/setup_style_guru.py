# File: setup_style_guru.py
# Run this from the my_framework directory

import sys
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Script directory: {script_dir}")

# Add the src directory to the path
sys.path.insert(0, os.path.join(script_dir, 'src'))

print("""
╔══════════════════════════════════════════════════════════════════╗
║                   STYLE GURU SETUP SCRIPT                        ║
║                                                                  ║
║  This will analyze 100 IntelliNews articles and create a        ║
║  comprehensive style framework for the AI to follow.            ║
║                                                                  ║
║  ⚠️  WARNING: This may take 15-30 minutes and use ~$2-5         ║
║      in OpenAI API credits (GPT-4 calls).                       ║
║                                                                  ║
║  You can run this anytime to update the framework with          ║
║  newer articles from IntelliNews.                               ║
╚══════════════════════════════════════════════════════════════════╝
""")

response = input("\nDo you want to proceed? (yes/y): ").strip().lower()

if response not in ['yes', 'y']:
    print("\n❌ Setup cancelled.")
    sys.exit(0)

print("\n" + "="*70)
print("STARTING STYLE GURU SETUP")
print("="*70)

# Load environment variables from .env file
print("\n[0/4] Loading environment variables...")
try:
    from dotenv import load_dotenv
    
    # Look for .env in the script directory (my_framework folder)
    dotenv_path = os.path.join(script_dir, '.env')
    print(f"   Checking: {dotenv_path}")
    
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"   ✅ Loaded .env file")
    else:
        print(f"   ⚠️ .env file not found at {dotenv_path}")
        print(f"   Trying parent directory...")
        
        # Try parent directory
        parent_dotenv = os.path.join(os.path.dirname(script_dir), '.env')
        if os.path.exists(parent_dotenv):
            load_dotenv(dotenv_path=parent_dotenv)
            print(f"   ✅ Loaded .env from {parent_dotenv}")
        else:
            print(f"   ⚠️ .env file not found")
            
except Exception as e:
    print(f"   ⚠️ Could not load .env file: {e}")

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("\n❌ ERROR: OPENAI_API_KEY not found!")
    print("\nTried:")
    print("  1. Environment variable OPENAI_API_KEY")
    print("  2. .env file in my_framework folder")
    print("\nPlease either:")
    print("  Option A - Set environment variable:")
    print("    Windows: set OPENAI_API_KEY=your-key-here")
    print("    Linux/Mac: export OPENAI_API_KEY=your-key-here")
    print("\n  Option B - Add to .env file:")
    print("    Create/edit my_framework/.env")
    print("    Add line: OPENAI_API_KEY=your-key-here")
    sys.exit(1)

print(f"\n✅ API key found: {api_key[:10]}...{api_key[-4:]}")

# Step 1: Deep Analysis
print("\n" + "─"*70)
print("STEP 1: DEEP ANALYSIS OF 100 ARTICLES")
print("─"*70)

try:
    from my_framework.style_guru.deep_analyzer import deep_style_analysis
    
    framework = deep_style_analysis(max_articles=100)
    
    if framework:
        print("\n✅ Deep analysis complete!")
    else:
        print("\n❌ Deep analysis failed!")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Error during deep analysis: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Build Training Dataset
print("\n" + "─"*70)
print("STEP 2: BUILD TRAINING DATASET FOR NEURAL SCORER")
print("─"*70)

try:
    from my_framework.style_guru.training import build_dataset
    
    build_dataset(limit=100)
    print("\n✅ Training dataset created!")
    
except Exception as e:
    print(f"\n❌ Error building dataset: {e}")
    import traceback
    traceback.print_exc()
    # Continue anyway - LLM scoring will still work

# Step 3: Train Neural Model
print("\n" + "─"*70)
print("STEP 3: TRAIN NEURAL STYLE SCORER")
print("─"*70)

try:
    from my_framework.style_guru.training import train_model
    
    train_model()
    print("\n✅ Neural model trained!")
    
except Exception as e:
    print(f"\n❌ Error training model: {e}")
    import traceback
    traceback.print_exc()
    # Continue anyway - LLM scoring will still work

# Step 4: Test the System
print("\n" + "─"*70)
print("STEP 4: TESTING THE SYSTEM")
print("─"*70)

try:
    from my_framework.style_guru.scorer import load_style_framework
    
    framework = load_style_framework()
    if framework:
        print("\n✅ Style framework loaded successfully!")
        print(f"   Framework version: {framework.get('version', 'unknown')}")
        print(f"   Articles analyzed: {framework.get('articles_analyzed', 'unknown')}")
    else:
        print("\n⚠️  Could not load framework, but files may still exist")
        
except Exception as e:
    print(f"\n❌ Error loading framework: {e}")

# Summary
print("\n" + "="*70)
print("SETUP COMPLETE!")
print("="*70)

print("""
The following files have been created:

1. intellinews_style_framework.json  - Comprehensive style framework (JSON)
2. intellinews_style_guide.txt       - Human-readable style guide
3. data/X.npy                        - Training features
4. data/y.npy                        - Training labels
5. data/model_weights.npz            - Trained neural model

You can now run the journalist bot and it will:
  ✓ Use the comprehensive style framework
  ✓ Score each article iteration
  ✓ Refine until it meets the quality threshold

The Style Guru is now active and will automatically improve all articles!
""")

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("""
1. Review the generated files (especially intellinews_style_guide.txt)
2. Run your journalist bot on a test URL
3. Monitor the iteration process in the logs
4. You can update the framework anytime by running this script again

To start the server:
  python run_local_server.bat
""")