from transformers import pipeline
import torch

device = 0 if torch.cuda.is_available() else -1  # 0 = first GPU, -1 = CPU
print("Using GPU" if device == 0 else "Using CPU")

generator = pipeline(
    "text-generation",
    model="Qwen/Qwen2.5-0.5B-Instruct",
    device=device,
    torch_dtype=torch.float16 
)

prompt = "Explain what a REST API is in simple terms."
output = generator(
    prompt,
    max_new_tokens=100,
    do_sample=True,
    temperature=0.7,
    top_p=0.9
)

print(output[0]["generated_text"])