import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Hugging Face API token from the environment variable
api_token = os.getenv("HUGGINGFACE_HUB_TOKEN")

# Load the Mistral model and tokenizer with a workaround for slow tokenization
model_name = "mistralai/Mistral-7B-Instruct-v0.3"
try:
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=api_token, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=api_token)
except ImportError as e:
    raise RuntimeError(f"Error loading model/tokenizer: {e}")

# Set the pad_token to eos_token
tokenizer.pad_token = tokenizer.eos_token

# Set up the FastAPI app
app = FastAPI()

class ModelRequest(BaseModel):
    prompt: str
    max_length: int

@app.post("/generate/")
async def generate_code(request: ModelRequest):
    try:
        # Tokenize the input and include the attention mask
        inputs = tokenizer(request.prompt, return_tensors="pt", padding=True, truncation=True, max_length=request.max_length)
        attention_mask = inputs.attention_mask
        
        # Generate the output with the attention mask and pad_token_id set
        outputs = model.generate(
            inputs.input_ids,
            attention_mask=attention_mask,
            max_length=request.max_length,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True
        )
        
        generated_code = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return {"generated_code": generated_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
