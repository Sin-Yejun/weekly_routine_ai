from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

BASE = os.getenv("NGROK_URL")

client = OpenAI(base_url=f"{BASE}/v1", api_key="token-1234")  # vLLM --api-key와 동일

resp = client.chat.completions.create(
    model="google/gemma-3-4b-it",
    messages=[
        {"role": "system", "content": "You are concise."},
        {"role": "user", "content": "이 터널 통해서 잘 연결됐나?"}
    ],
    max_tokens=5000,
)
print(resp.choices[0].message.content)

# 서버 실행 코드
'''
python -m vllm.entrypoints.openai.api_server \
  --model google/gemma-3-4b-it \
  --dtype bfloat16 \
  --api-key token-1234 \
  --host 127.0.0.1 --port 8000 \
  --trust-remote-code \
  --gpu-memory-utilization 0.4 \
  --max-model-len 8192
  --enable-lora \
  --lora-modules mygemma=../out/gemma3-4b-it-sft-qlora-fa2/checkpoint-2795
'''
# ngrok 실행
# ngrok http 8000