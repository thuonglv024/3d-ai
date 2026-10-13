import json

with open(r"C:\Users\Phan Trinh Tien Dat\.gemini\antigravity\brain\8eb7826c-d1b9-40cb-9702-656e36d73828\.system_generated\logs\transcript.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        if idx in range(940, 954):
            print(f"=== Step {idx} ({obj.get('type')}) ===")
            if 'tool_calls' in obj:
                for tc in obj['tool_calls']:
                    print(f"  Tool: {tc['name']}")
                    args = tc.get('args', {})
                    if 'CommandLine' in args:
                        print(f"    CMD: {args['CommandLine'][:100]}")
                    if 'query' in args:
                        print(f"    Query: {args['query']}")
                    if 'TargetFile' in args:
                        print(f"    TargetFile: {args['TargetFile']}")
            if 'thinking' in obj:
                print(f"  Thinking: {obj['thinking'][:200]}...")
