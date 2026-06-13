import requests

def get_bible_verse(passage: str):
    # A simple tool using a free, no-auth API
    response = requests.get(f"https://bible-api.com/{passage}")
    return response.json().get("text", "Verse not found.")

def run_agentic_study(user_prompt):
    messages = [
        {"role": "system", "content": "You are a Bible study assistant. You have access to a tool called get_bible_verse(passage). You MUST verify verses using this tool before writing your final summary."},
        {"role": "user", "content": user_prompt}
    ]
    
    # Simple loop to handle the agent's thoughts and actions
    for _ in range(5):  # Max 5 iterations to prevent infinite loops
        response = call_llm(messages) # Your standard LLM API call
        messages.append({"role": "assistant", "content": response})
        
        if "FINAL_ANSWER" in response:
            break
            
        if "CALL_TOOL:" in response:
            # Parse the passage the LLM wants to look up
            passage = parse_passage(response) 
            tool_result = get_bible_verse(passage)
            
            # Feed the real data back into the loop
            messages.append({"role": "user", "content": f"Tool Result: {tool_result}"})
            
    return messages[-1]["content"]
