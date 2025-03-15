import asyncio

from rai.agentic.aether.aether import AEther


async def main():
    agent = AEther()
    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            print("Empty prompt provided.")
            return

        print("Processing your request...")
        await agent.run(prompt)
        print("Request processing completed.")
    except KeyboardInterrupt:
        print("Operation interrupted.")


if __name__ == "__main__":
    asyncio.run(main())