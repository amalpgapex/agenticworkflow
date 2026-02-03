from agent_framework_devui import serve
from dotenv import load_dotenv
def main() -> None:
    load_dotenv(override=True)
    serve(entities_dir="./agent_framework_devui/workflows/")

if __name__ == "__main__":
    main()