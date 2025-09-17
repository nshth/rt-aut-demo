import asyncio
import warnings
from backend.service.whatsapp_service import WhatsAppService

# --- Silencing deprecation warnings ---
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- CLI colors ---
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
WHITE = "\033[0;39m"

wa_service = WhatsAppService()  

async def main():
    print(f"{YELLOW}" + "-"*81)
    print("CLI WhatsApp Test. Type your message:")
    print("-"*81 + f"{WHITE}")

    from_number = "cli_test_user"

    while True:
        query = input(f"{GREEN}Prompt: ").strip()
        if query.lower() in ["exit", "quit", "q", "f"]:
            print("Exiting")
            break
        if not query:
            continue

        # Directly call process_single_message and await result
        reply = await wa_service.process_single_message(from_number, query)

if __name__ == "__main__":
    asyncio.run(main())
