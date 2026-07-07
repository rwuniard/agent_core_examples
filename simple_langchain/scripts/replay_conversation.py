"""
Replay the "what is my name?" failure scenario N times to check whether the
refusal is deterministic (same every time -> points at a Guardrail or fixed
logic) or stochastic (varies run to run -> points at model sampling /
"lost in the middle" with long tool-call context).

Each trial gets a fresh actor_id/thread_id (no cross-trial memory pollution)
and replays:
    1. "hi my name is Rob."
    2. "what's on the stock market today?"   (triggers a tool call, same as
       the logged failures)
    3. "what is my name?"

Usage:
    cd simple_langchain
    uv run python scripts/replay_conversation.py --trials 5
    uv run python scripts/replay_conversation.py --trials 5 --temperature 0
"""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import SimpleLangchainAgent  # noqa: E402

REFUSAL_MARKERS = (
    "can't share",
    "cannot share",
    "can't provide",
    "cannot provide",
    "personal information",
    "without their consent",
    "without your consent",
)


def classify(response: str) -> str:
    lowered = response.lower()
    if any(marker in lowered for marker in REFUSAL_MARKERS):
        return "REFUSED"
    if "rob" in lowered:
        return "REMEMBERED"
    return "UNKNOWN"


async def run_trial(agent: SimpleLangchainAgent, trial_num: int) -> str:
    actor_id = f"replay-{uuid.uuid4()}"
    thread_id = str(uuid.uuid4())
    print(f"\n=== Trial {trial_num} (actor_id={actor_id}, thread_id={thread_id}) ===")

    for message in (
        "hi my name is Rob.",
        "what's on the stock market today?",
    ):
        await agent.invoke_async(message, actor_id=actor_id, thread_id=thread_id)

    final_response = await agent.invoke_async(
        "what is my name?", actor_id=actor_id, thread_id=thread_id
    )
    verdict = classify(final_response)
    print(f"[trial {trial_num}] verdict={verdict}")
    print(f"[trial {trial_num}] response={final_response!r}")
    return verdict


async def main_async(trials: int, temperature: float | None) -> None:
    agent = SimpleLangchainAgent(temperature=temperature)
    verdicts = []
    for i in range(1, trials + 1):
        verdict = await run_trial(agent, i)
        verdicts.append(verdict)

    print("\n=== Summary ===")
    print(f"temperature={temperature!r}  trials={trials}")
    for verdict in ("REMEMBERED", "REFUSED", "UNKNOWN"):
        count = verdicts.count(verdict)
        print(f"  {verdict}: {count}/{trials}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the name-recall scenario N times")
    parser.add_argument("--trials", type=int, default=5, help="Number of trials to run")
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Model temperature to use (omit to use the provider default)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args.trials, args.temperature))
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
