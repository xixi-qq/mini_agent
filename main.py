import argparse

from agent import AgentRuntime
from agent.llm import OpenAICompatibleLLM


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Agent Runtime CLI")
    parser.add_argument("--session", default="default", help="Session id, for example window1")
    args = parser.parse_args()

    runtime = AgentRuntime(llm=OpenAICompatibleLLM())
    print(f"session={args.session}. Type /exit to quit.")
    while True:
        user_input = input("user> ").strip()
        if user_input in {"/exit", "/quit"}:
            break
        if not user_input:
            continue
        answer = runtime.run(args.session, user_input)
        print(f"agent> {answer}")


if __name__ == "__main__":
    main()
