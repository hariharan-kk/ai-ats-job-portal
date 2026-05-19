import google.generativeai as genai

# Put your NEW API key inside the quotes here:
genai.configure(api_key="AIzaSyDEy1ikfACnBVLlyV519pFAggg7oQd0fxM")

print("--- AVAILABLE MODELS ---")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)