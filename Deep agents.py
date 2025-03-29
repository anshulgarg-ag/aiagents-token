import ggwave
import pyaudio
import time
import google.generativeai as genai
import sys

# Set up Gemini API Key
genai.configure(api_key="AIzaSyDuqQq_xckOVNuDU-WDc-5qWZevE2g0oY8")

# Initialize PyAudio and GGWave
p = pyaudio.PyAudio()
instance = ggwave.init()

# Get role from command line
role = sys.argv[1] if len(sys.argv) > 1 else "patient"

# Open audio streams
input_stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=1024)
output_stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, output=True, frames_per_buffer=4096)

print(f"Starting as {role.capitalize()} Agent...")

def get_role_prompt(role, message):
    """Generate role-specific prompt for Gemini"""
    if role == "doctor":
        return f"""You are a doctor's receptionist. Your task is to:
1. Ask for patient's name
2. Ask for preferred appointment date and time
3. Ask brief reason for visit
4. Confirm appointment details
Keep responses under 2 sentences. Current conversation:
Patient: {message}
Doctor:"""
    else:
        return f"""You are a patient wanting to book an appointment. Your task is to:
1. Provide your full name
2. Share preferred availability
3. Mention brief reason for visit
4. Confirm details when asked
Keep responses under 2 sentences. Current conversation:
Doctor: {message}
Patient:"""

def chat_with_gemini(prompt):
    """Get response from Gemini API."""
    try:
        model = genai.GenerativeModel(
            "gemini-1.5-pro-latest",
            generation_config={
                "temperature": 0.7,  # Increased for more natural conversation
                "max_output_tokens": 300  # Longer responses allowed
            },
            system_instruction="Maintain your assigned role strictly. Keep responses conversational."
        )

        # Use chat interface for better context retention
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini API Error:", e)
        return "Could you please repeat that?"

# Send initial message if patient
if role == "patient":
    initial_message = "Hello, I'd like to book a doctor's appointment."
    waveform = ggwave.encode(initial_message, protocolId=1, volume=20)
    output_stream.write(waveform, len(waveform)//4)
    print(f"Patient: {initial_message}")
    time.sleep(2)  # Wait for transmission

try:
    while True:
        # Receive and decode message
        data = input_stream.read(1024, exception_on_overflow=False)
        received_text = ggwave.decode(instance, data)

        if received_text:
            try:
                message = received_text.decode("utf-8")
                print(f"Received ({role}): {message}")

                # Generate role-specific response
                prompt = get_role_prompt(role, message)
                response_text = chat_with_gemini(prompt)
                print(f"{role.capitalize()}: {response_text}")

                # Transmit response
                waveform = ggwave.encode(response_text, protocolId=1, volume=20)
                output_stream.write(waveform, len(waveform)//4)
                time.sleep(2)  # Pause between exchanges

            except Exception as e:
                print("Error:", e)

except KeyboardInterrupt:
    print("Stopping Agent...")

# Cleanup
ggwave.free(instance)
input_stream.stop_stream()
input_stream.close()
output_stream.stop_stream()
output_stream.close()
p.terminate()