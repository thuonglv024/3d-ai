import json

with open(r"C:\Users\Phan Trinh Tien Dat\.gemini\antigravity\brain\8eb7826c-d1b9-40cb-9702-656e36d73828\.system_generated\logs\transcript.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('step_index') in [951, 953]:
            print(f"=== Step {obj.get('step_index')} ===")
            if 'thinking' in obj:
                print('Thinking:', obj['thinking'][:600])
            if 'tool_calls' in obj:
                for tc in obj['tool_calls']:
                    print('Tool call:', tc['name'], tc.get('args', {}).keys())
