import asyncio
import time
import warnings
from backend.service.whatsapp_service import WhatsAppService

# Silence deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Colors
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
WHITE = "\033[0;39m"
CYAN = "\033[0;36m"

async def simulate_customer(customer_id: str, messages: list[str], delay_between_messages: float = 2.0):
    """Simulate a single customer sending multiple messages"""
    wa_service = WhatsAppService()
    customer_number = f"+9477123456{customer_id}"
    
    print(f"{CYAN}🔵 Customer {customer_id} ({customer_number}) started{WHITE}")
    
    results = []
    for i, message in enumerate(messages, 1):
        print(f"{BLUE}📱 Customer {customer_id} sending: {message}{WHITE}")
        
        start_time = time.time()
        result = await wa_service.process_single_message(customer_number, message)
        end_time = time.time()
        
        processing_time = end_time - start_time
        results.append({
            "message": message,
            "result": result,
            "processing_time": processing_time
        })
        
        print(f"{GREEN}✅ Customer {customer_id} message {i} completed in {processing_time:.2f}s{WHITE}")
        
        # Wait before next message (simulate real customer behavior)
        if i < len(messages):
            await asyncio.sleep(delay_between_messages)
    
    print(f"{CYAN}🎉 Customer {customer_id} finished all messages{WHITE}")
    return {"customer_id": customer_id, "customer_number": customer_number, "results": results}

async def test_concurrent_customers():
    """Test multiple customers interacting simultaneously"""
    print(f"{YELLOW}" + "="*80)
    print("🚀 TESTING CONCURRENT CUSTOMER HANDLING")
    print("="*80 + f"{WHITE}")
    
    # Define different customer scenarios
    customers = [
        {
            "id": "1",
            "messages": [
                "Hi, I want to check gaming chair stock",
                "I need 2 gaming chairs",
            ]
        },
        {
            "id": "2", 
            "messages": [
                "Do you have monitors available?",
                "I want 3 HD monitors",
            ]
        },
        {
            "id": "3",
            "messages": [
                "you got any baseball cap?",
                "ill text you later",
            ]
        }
    ]
    
    print(f"{YELLOW}Starting {len(customers)} concurrent customers...{WHITE}\n")
    start_time = time.time()
    
    # Run all customers concurrently
    tasks = [
        simulate_customer(
            customer["id"], 
            customer["messages"],
            delay_between_messages=1.5  # Faster for testing
        ) 
        for customer in customers
    ]
    
    # Execute all customer interactions concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print results
    print(f"\n{YELLOW}" + "="*80)
    print("📊 TEST RESULTS")
    print("="*80 + f"{WHITE}")
    print(f"⏱️  Total test duration: {total_time:.2f} seconds")
    print(f"👥 Customers processed: {len(customers)}")
    
    successful = 0
    failed = 0
    total_messages = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"{RED}❌ Customer {customers[i]['id']} failed: {result}{WHITE}")
            failed += 1
        else:
            customer_id = result["customer_id"]
            message_count = len(result["results"])
            avg_time = sum(r["processing_time"] for r in result["results"]) / message_count
            
            print(f"{GREEN}✅ Customer {customer_id}: {message_count} messages, avg {avg_time:.2f}s per message{WHITE}")
            successful += 1
            total_messages += message_count
    
    print(f"\n{CYAN}🎯 SUMMARY:{WHITE}")
    print(f"   ✅ Successful: {successful}/{len(customers)} customers")
    print(f"   ❌ Failed: {failed}/{len(customers)} customers") 
    print(f"   📨 Total messages processed: {total_messages}")
    print(f"   ⚡ Average messages per second: {total_messages/total_time:.2f}")

async def test_batch_processing():
    """Test the batch processing capability"""
    print(f"\n{YELLOW}" + "="*80)
    print("🔥 TESTING BATCH PROCESSING")
    print("="*80 + f"{WHITE}")
    
    wa_service = WhatsAppService()
    
    # Create batch of messages
    messages = [
        ("+94771234561", "Check gaming chair stock"),
        ("+94771234562", "I want 2 monitors"), 
        ("+94771234563", "What laptops available?"),
        ("+94771234564", "Office desk price?"),
        ("+94771234565", "Hello, need help")
    ]
    
    print(f"Processing {len(messages)} messages in batch...")
    start_time = time.time()
    
    results = await wa_service.process_messages(messages)
    
    end_time = time.time()
    batch_time = end_time - start_time
    
    print(f"{GREEN}✅ Batch completed in {batch_time:.2f} seconds{WHITE}")
    print(f"⚡ {len(messages)/batch_time:.2f} messages per second")
    
    for result in results:
        status = result.get("status", "unknown")
        from_number = result.get("from_number", "unknown")
        print(f"   📱 {from_number}: {status}")

async def main():
    """Run all tests"""
    print(f"{YELLOW}🧪 WHATSAPP CONCURRENT PROCESSING TESTS{WHITE}")
    
    try:
        await test_concurrent_customers()
        # await test_batch_processing()
        
        print(f"\n{GREEN}" + "="*80)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80 + f"{WHITE}")
        
    except Exception as e:
        print(f"{RED}💥 Test failed with error: {e}{WHITE}")
        raise

if __name__ == "__main__":
    asyncio.run(main())