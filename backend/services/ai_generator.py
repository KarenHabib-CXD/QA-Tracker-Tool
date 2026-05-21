import json
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _mock_test_cases(title: str, description: str, ticket_type: str) -> List[Dict]:
    """Fallback mock generator when no OpenAI key is configured."""
    base = [
        {
            "title": f"Happy path – {title}",
            "preconditions": "User is logged in and app is on latest version.",
            "steps": json.dumps([
                "Navigate to the relevant screen",
                "Perform the main action described in the ticket",
                "Verify the result"
            ]),
            "expected_result": "Feature works as described in the acceptance criteria.",
            "priority": "High",
            "tags": "smoke,regression"
        },
        {
            "title": f"Negative path – invalid input for {title}",
            "preconditions": "User is logged in.",
            "steps": json.dumps([
                "Navigate to the relevant screen",
                "Enter invalid / empty data",
                "Submit / confirm"
            ]),
            "expected_result": "Appropriate error message is displayed and no data is corrupted.",
            "priority": "High",
            "tags": "regression"
        },
        {
            "title": f"Edge case – boundary conditions for {title}",
            "preconditions": "User is logged in.",
            "steps": json.dumps([
                "Navigate to the relevant screen",
                "Test with minimum / maximum allowed values",
                "Verify behaviour at boundaries"
            ]),
            "expected_result": "Application handles boundary values gracefully.",
            "priority": "Medium",
            "tags": "regression"
        },
        {
            "title": f"UI/UX – layout and accessibility for {title}",
            "preconditions": "App is open on the target screen.",
            "steps": json.dumps([
                "Open the screen on various device sizes",
                "Check labels, buttons and spacing",
                "Verify accessibility labels are present"
            ]),
            "expected_result": "UI is consistent and accessible across all target devices.",
            "priority": "Low",
            "tags": "ui,accessibility"
        },
    ]

    if ticket_type == "bug":
        base.insert(0, {
            "title": f"Regression – verify bug fix for {title}",
            "preconditions": "App updated to the build containing the fix.",
            "steps": json.dumps([
                "Reproduce the exact steps from the original bug report",
                "Verify the bug no longer occurs"
            ]),
            "expected_result": "Bug is resolved and original scenario works correctly.",
            "priority": "Critical",
            "tags": "regression,bug-fix"
        })

    return base


def generate_test_cases(title: str, description: str, ticket_type: str = "feature") -> List[Dict]:
    """Generate test cases using GitHub Models API if token available, otherwise use mock data."""

    if not GITHUB_TOKEN or GITHUB_TOKEN == "paste_your_ghp_token_here":
        return _mock_test_cases(title, description, ticket_type)

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=GITHUB_TOKEN,
        )

        prompt = f"""You are a senior QA engineer. Generate comprehensive test cases for the following ticket.

Ticket Type: {ticket_type}
Title: {title}
Description: {description}

Return a JSON array (no markdown, pure JSON) where each item has these exact keys:
- title: short test case title
- preconditions: what must be true before the test
- steps: JSON array of step strings
- expected_result: what should happen
- priority: one of Critical / High / Medium / Low
- tags: comma-separated tags from: smoke, regression, ui, accessibility, bug-fix, performance

Include: happy path, negative/invalid input, edge cases, UI/UX checks.
For bug tickets also add a regression verification case.
Return between 4-8 test cases."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Handle both {"test_cases": [...]} and [...]
        if isinstance(parsed, list):
            cases = parsed
        elif "test_cases" in parsed:
            cases = parsed["test_cases"]
        else:
            cases = list(parsed.values())[0]

        # Ensure steps is always a JSON string
        for case in cases:
            if isinstance(case.get("steps"), list):
                case["steps"] = json.dumps(case["steps"])

        return cases

    except Exception as e:
        print(f"[AI Generator] GitHub Models failed ({e}), falling back to mock.")
        return _mock_test_cases(title, description, ticket_type)
