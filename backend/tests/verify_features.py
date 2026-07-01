import asyncio
import os
import sys

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.command_runner import command_runner
from app.services.playwright_client import playwright_browser
from app.services.research_service import research_service
from app.core.config import settings

async def verify_command_approval():
    print("\n--- Verifying Command Approval Workflow ---")
    # 1. Register a challenge command (notepad.exe)
    cmd = 'echo "Operation approved successfully"'
    desc = "Test authorization safety check"
    challenge_id = command_runner.register_challenge(cmd, desc)
    print(f"Registered safety challenge. ID: {challenge_id}")
    
    # Verify challenge is in registry
    challenge = command_runner.get_challenge(challenge_id)
    assert challenge is not None
    assert challenge["command"] == cmd
    print(f"Verified challenge matches command: {challenge['command']}")
    
    # 2. Execute the approved challenge
    code, stdout, stderr = command_runner.execute_approved_challenge(challenge_id)
    print(f"Execution complete. Return Code: {code}")
    print(f"Stdout: {stdout.strip()}")
    print(f"Stderr: {stderr.strip()}")
    
    assert code == 0
    assert "approved" in stdout
    print("Command Approval safety workflow verified: PASS")


async def verify_playwright():
    print("\n--- Verifying Playwright Web Retrieve ---")
    # Fetch content of a lightweight page (example.com)
    url = "https://example.com"
    print(f"Opening browser to: {url}...")
    try:
        data = await playwright_browser.fetch_page_content(url)
        print(f"Page Title retrieved: '{data['title']}'")
        print(f"Content length: {len(data['content'])} characters")
        assert "Example Domain" in data["title"]
        assert len(data["content"]) > 0
        print("Playwright web retrieval verified: PASS")
    except Exception as e:
        print(f"Playwright web retrieval failed: {str(e)}")
        raise e


async def verify_research_service():
    print("\n--- Verifying Research Service Pipeline ---")
    
    # Test 1: Without Gemini API key (Heuristic Fallback)
    print("Test 1: Running WITHOUT Gemini key (using simulated mock key or removing settings key)...")
    original_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = None
    research_service.gemini_configured = False
    
    try:
        report = await research_service.compile_research_report("machine learning")
        print(f"Report Title: '{report['title']}'")
        print(f"Summary: '{report['summary']}'")
        print(f"Content snippet (Fallback):\n{report['content'][:250]}...")
        assert "Heuristic" in report["content"] or "Consolidated" in report["summary"] or "Could not scrape" in report["summary"]
        assert len(report["sources"]) > 0
        print("Test 1 (No Gemini Key) verified: PASS")
    except Exception as e:
        print(f"Research Service without Gemini key failed: {str(e)}")
        raise e
        
    # Test 2: With Gemini API key (if configured, else skip with message)
    if original_key:
        print("\nTest 2: Running WITH Gemini key...")
        settings.GEMINI_API_KEY = original_key
        research_service.gemini_configured = True
        try:
            report = await research_service.compile_research_report("machine learning")
            print(f"Report Title: '{report['title']}'")
            print(f"Summary: '{report['summary']}'")
            print(f"Content snippet (Gemini):\n{report['content'][:250]}...")
            assert len(report["sources"]) > 0
            print("Test 2 (Gemini Key active) verified: PASS")
        except Exception as e:
            print(f"Research Service with Gemini key failed: {str(e)}")
            raise e
    else:
        print("\nTest 2: Skipping Gemini API check (No key found in environmental settings).")
        print("Heuristic parsing is functional, which serves as the proper fallback.")


async def main():
    try:
        await verify_command_approval()
        await verify_playwright()
        await verify_research_service()
        print("\n==============================")
        print("ALL VERIFICATION CHECKS PASSED")
        print("==============================")
    finally:
        # Clean up browser session
        await playwright_browser.close()

if __name__ == "__main__":
    asyncio.run(main())
