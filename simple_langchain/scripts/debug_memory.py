"""
Diagnostic script for AgentCoreMemorySaver checkpoint retrieval.

Usage:
    cd simple_langchain
    uv run python scripts/debug_memory.py \
        --session-id <session_id> \
        --actor-id <actor_id>

The session_id and actor_id must match exactly what was used in test_local.sh
(e.g. session_id="f0942990-b1b5-4754-b25d-a3bd98233b1b", actor_id="test-actor-2").
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Debug AgentCoreMemorySaver checkpoint retrieval")
    parser.add_argument("--session-id", required=True, help="thread_id / session_id used in test calls")
    parser.add_argument("--actor-id", required=True, help="actor_id used in test calls")
    args = parser.parse_args()

    memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
    if not memory_id:
        print("ERROR: AGENTCORE_MEMORY_ID env var not set", file=sys.stderr)
        sys.exit(1)

    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    print(f"Memory ID  : {memory_id}")
    print(f"Region     : {region}")
    print(f"Session ID : {args.session_id}")
    print(f"Actor ID   : {args.actor_id}")
    print()

    from langgraph_checkpoint_aws import AgentCoreMemorySaver

    saver = AgentCoreMemorySaver(memory_id=memory_id, region_name=region)

    # ── 1. Raw event count ──────────────────────────────────────────────────
    print("=== Step 1: Raw ListEvents ===")
    raw_events = saver.checkpoint_event_client.get_events(
        session_id=args.session_id,
        actor_id=args.actor_id,
    )
    print(f"Total events returned by ListEvents: {len(raw_events)}")
    for i, ev in enumerate(raw_events):
        print(f"  [{i}] type={ev.event_type!r}  ", end="")
        if hasattr(ev, "checkpoint_id"):
            print(f"checkpoint_id={ev.checkpoint_id!r}", end="")
        if hasattr(ev, "channel"):
            print(f"channel={ev.channel!r} version={ev.version!r}", end="")
        print()
    print()

    # ── 2. get_tuple ────────────────────────────────────────────────────────
    print("=== Step 2: get_tuple ===")
    config = {
        "configurable": {
            "thread_id": args.session_id,
            "actor_id": args.actor_id,
        }
    }
    result = saver.get_tuple(config)

    if result is None:
        print("get_tuple returned None — no checkpoint found for this session/actor")
    else:
        print("get_tuple returned a CheckpointTuple!")
        checkpoint = result.checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        print(f"  checkpoint_id  : {checkpoint.get('id')!r}")
        print(f"  channels       : {list(channel_values.keys())}")
        print(f"  message count  : {len(messages)}")
        for j, msg in enumerate(messages):
            role = getattr(msg, "type", type(msg).__name__)
            content = getattr(msg, "content", str(msg))
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c)
                    for c in content
                )
            print(f"    [{j}] {role}: {str(content)[:120]!r}")
    print()

    # ── 3. list() ────────────────────────────────────────────────────────────
    print("=== Step 3: list() — all checkpoints for this session ===")
    count = 0
    for cp in saver.list(config):
        count += 1
        print(f"  checkpoint {count}: id={cp.checkpoint.get('id')!r}  parent={cp.parent_config}")
    if count == 0:
        print("  (none)")


if __name__ == "__main__":
    main()
