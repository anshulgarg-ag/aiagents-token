import ggwave
import pyaudio
import time
import google.generativeai as genai
import os

# Set up Gemini API Key (Replace with your actual key or use an env variable)
genai.configure(api_key="AIzaSyDuqQq_xckOVNuDU-WDc-5qWZevE2g0oY8")

# Initialize PyAudio and GGWave
p = pyaudio.PyAudio()
instance = ggwave.init()

# Open audio streams
input_stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=1024)
output_stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, output=True, frames_per_buffer=4096)

print("AI Agent is listening...")

def chat_with_gemini(prompt):
    """Get response from Gemini API."""
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")  # Use "gemini-1.5-pro" for better responses
        response = model.generate_content(prompt)
        system_instruction = "give me answer in only 20 words\n"
        return response.text.strip()
    except Exception as e:
        print("Gemini API Error:", e)
        return "I'm having trouble responding right now."

try:
    while True:
        # Receive and decode the message
        data = input_stream.read(1024, exception_on_overflow=False)
        received_text = ggwave.decode(instance, data)

        if received_text:
            try:
                message = received_text.decode("utf-8")
                print(f"Received: {message}")

                # Generate response using Gemini
                response_text = chat_with_gemini(message)
                print(f"AI Response: {response_text}")

                # Encode and transmit the response
                waveform = ggwave.encode(response_text, protocolId=1, volume=20)
                output_stream.write(waveform, len(waveform)//4)
                time.sleep(1)  # Prevent audio overlap

            except Exception as e:
                print("Error:", e)

except KeyboardInterrupt:
    print("Stopping AI Agent...")

# Cleanup
ggwave.free(instance)
input_stream.stop_stream()
input_stream.close()
output_stream.stop_stream()
output_stream.close()
p.terminate()