import asyncio
import httpx
import json

API_URL = "http://localhost:8000/api/agent/message"

CUSTOMERS = {
    "1": {"id": "7b1e359b-e01a-5a2d-ae0c-5cb09e4a5e84", "name": "Amara Chen (Recent order: Shoes)"},
    "2": {"id": "8bf621ad-b367-56e5-9442-d1c1039b69f4", "name": "Jordan Reyes (Broken items)"},
    "3": {"id": "7c0028d1-9b02-5498-9b6f-cb94bdb9f0e6", "name": "Priya Nair"}
}

async def main():
    print("=" * 50)
    print("⚡ ReturnPilot CLI Agent Chat ⚡")
    print("=" * 50)
    print("Choose a customer to act as:")
    for k, v in CUSTOMERS.items():
        print(f"[{k}] {v['name']}")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    customer = CUSTOMERS.get(choice, CUSTOMERS["1"])
    print(f"\n--- Chatting as {customer['name']} ---")
    print("Type 'exit' or 'quit' to stop.\n")
    
    conversation_history = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            msg = input("You: ").strip()
            if msg.lower() in ['exit', 'quit']:
                print("Ending chat. Goodbye!")
                break
            if not msg:
                continue
                
            print("🤖 Agent is thinking (running multi-agent loop, wait 10-20s)...")
            
            payload = {
                "customer_id": customer["id"],
                "message": msg,
                "conversation_history": conversation_history
            }
            
            try:
                response = await client.post(API_URL, json=payload)
                if response.status_code != 200:
                    print(f"\n❌ Error {response.status_code}: {response.text}")
                    continue
                    
                data = response.json()
                
                print(f"\nAgent: {data['response']}")
                
                # Show trace details
                print("\n" + "-" * 40)
                print("🧠 Multi-Agent Reasoning Trace Summary:")
                for step in data.get('reasoning_trace', []):
                    if step['agent'] == 'nlp_analyzer':
                        res = step.get('result', {})
                        print(f"  [NLP Analyzer] Detected '{res.get('reason_classification')}' with {res.get('sentiment')} sentiment")
                    elif step.get('tool'):
                        print(f"  [{step['agent']}] Used tool: {step['tool']}")
                    elif "Final response" in str(step.get('decision')):
                        print(f"  [Orchestrator] Generated final response.")
                print("-" * 40 + "\n")
                
                # Update history for multi-turn chat
                conversation_history.append({"role": "user", "content": [{"type": "text", "text": msg}]})
                conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": data['response']}]})
                
            except Exception as e:
                print(f"\n❌ Connection Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
