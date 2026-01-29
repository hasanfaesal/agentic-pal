import os
from auth import build_service
from services.calendar import CalendarService
from services.gmail import GmailService
from services.tasks import TasksService
from agent.graph.graph_builder import create_graph_runner
from agent.graph.prompts import use_dspy, use_legacy, is_dspy_mode, PromptConfig

def main():
    # 1. Initialize Google Services
    calendar_service = CalendarService(build_service("calendar", "v3"))
    gmail_service = GmailService(build_service("gmail", "v1"))
    tasks_service = TasksService(build_service("tasks", "v1"))
    
    # 2. Configure prompt mode
    # Choose one:
    # - use_legacy() for traditional LangChain prompts (more stable)
    # - Configure DSPy for structured prompts (experimental)
    
    # Option A: Use Legacy mode (recommended for now)
    use_legacy()
    
    # Option B: Use DSPy mode with Mistral (uncomment to use)
    # PromptConfig.configure_dspy(
    #     model="mistral/mistral-large-latest",
    #     api_key=os.environ.get("MISTRAL_API_KEY"),
    # )
    
    # 3. Build the graph runner
    graph, tools_registry = create_graph_runner(
        calendar_service=calendar_service,
        gmail_service=gmail_service,
        tasks_service=tasks_service,
        model_name="qwen-plus-2025-12-01",
        default_timezone="UTC"
    )
    
    # 4. REPL Loop
    print("AgenticPal - Your AI Personal Assistant")
    print("Type 'exit', 'quit', or 'q' to exit")
    print(f"Mode: {'DSPy' if is_dspy_mode() else 'Legacy'}")
    print("-" * 50)
    
    config = {"configurable": {"thread_id": "main"}}
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break
            
            if user_input.lower() == "help":
                print(tools_registry.get_tool_descriptions())
                continue
            
            # Run the graph
            result = graph.invoke(
                {"user_message": user_input, "conversation_history": []},
                config
            )
            
            print(f"\n  Assistant: {result['final_response']}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue

if __name__ == "__main__":
    main()