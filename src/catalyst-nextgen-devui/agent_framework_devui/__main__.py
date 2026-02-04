import asyncio
from agent_framework_devui import serve
from dotenv import load_dotenv
from agent_framework_devui.workflows import create_comparison_workflow


if __name__ == "__main__":
    load_dotenv(override=True)
    compare_contents = asyncio.run(create_comparison_workflow())
    serve(entities=[compare_contents])