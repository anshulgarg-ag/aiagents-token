# import ggwave
# import pyaudio
# import time
# import google.generativeai as genai
# import sys
#
# # Set up Gemini API Key
# genai.configure(api_key="AIzaSyDuqQq_xckOVNuDU-WDc-5qWZevE2g0oY8")
#
# # Initialize PyAudio and GGWave
# p = pyaudio.PyAudio()
# instance = ggwave.init()
#
# # Get role from command line
# role = sys.argv[1] if len(sys.argv) > 1 else "patient"
#
# # Open audio streams
# input_stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=1024)
# output_stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, output=True, frames_per_buffer=4096)
#
# print(f"Starting as {role.capitalize()} Agent...")
#
# def get_role_prompt(role, message):
#     """Generate role-specific prompt for Gemini"""
#     if role == "doctor":
#         return f"""You are a doctor's receptionist. Your task is to:
# 1. Ask for patient's name
# 2. Ask for preferred appointment date and time
# 3. Ask brief reason for visit
# 4. Confirm appointment details
# Keep responses under 2 sentences. Current conversation:
# Patient: {message}
# Doctor:"""
#     else:
#         return f"""You are a patient wanting to book an appointment. Your task is to:
# 1. Provide your full name
# 2. Share preferred availability
# 3. Mention brief reason for visit
# 4. Confirm details when asked
# Keep responses under 2 sentences. Current conversation:
# Doctor: {message}
# Patient:"""
#
# def chat_with_gemini(prompt):
#     """Get response from Gemini API."""
#     try:
#         model = genai.GenerativeModel("gemini-1.0-pro")
#         response = model.generate_content(prompt)
#         return response.text.strip()
#     except Exception as e:
#         print("Gemini API Error:", e)
#         return "Could you please repeat that?"
#
# # Send initial message if patient
# if role == "patient":
#     initial_message = "Hello, I'd like to book a doctor's appointment."
#     waveform = ggwave.encode(initial_message, protocolId=1, volume=20)
#     output_stream.write(waveform, len(waveform)//4)
#     print(f"Patient: {initial_message}")
#     time.sleep(2)  # Wait for transmission
#
# try:
#     while True:
#         # Receive and decode message
#         data = input_stream.read(1024, exception_on_overflow=False)
#         received_text = ggwave.decode(instance, data)
#
#         if received_text:
#             try:
#                 message = received_text.decode("utf-8")
#                 print(f"Received ({role}): {message}")
#
#                 # Generate role-specific response
#                 prompt = get_role_prompt(role, message)
#                 response_text = chat_with_gemini(prompt)
#                 print(f"{role.capitalize()}: {response_text}")
#
#                 # Transmit response
#                 waveform = ggwave.encode(response_text, protocolId=1, volume=20)
#                 output_stream.write(waveform, len(waveform)//4)
#                 time.sleep(2)  # Pause between exchanges
#
#             except Exception as e:
#                 print("Error:", e)
#
# except KeyboardInterrupt:
#     print("Stopping Agent...")
#
# # Cleanup
# ggwave.free(instance)
# input_stream.stop_stream()
# input_stream.close()
# output_stream.stop_stream()
# output_stream.close()
# p.terminate()
import ggwave
import pyaudio
import time
import google.generativeai as genai
# import sys # No longer needed

# --- Configuration ---
# !!! IMPORTANT: Replace with your actual API key !!!
# Consider using environment variables for security in real applications
GEMINI_API_KEY = "AIzaSyDuqQq_xckOVNuDU-WDc-5qWZevE2g0oY8" # Replace with your key

# Audio Settings
INPUT_FORMAT = pyaudio.paFloat32
OUTPUT_FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 48000
INPUT_FRAMES_PER_BUFFER = 1024
OUTPUT_FRAMES_PER_BUFFER = 4096 # Larger buffer for potentially longer AI responses

# GGWave Settings
PROTOCOL_ID = 4  # Choose a ggwave protocol (e.g., 1: 'audible-fast')
VOLUME = 20      # Transmission volume (0-100)
TX_PAUSE_DURATION = 2.0 # Seconds to pause after transmitting

# Role (Hardcoded for this version)
ROLE = "doctor"
# --- End Configuration ---


# Set up Gemini API Key
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    print("Please ensure your API key is correct and valid.")
    exit()

# Initialize PyAudio and GGWave
try:
    p = pyaudio.PyAudio()
    instance = ggwave.init()
except Exception as e:
    print(f"Error initializing PyAudio/GGWave: {e}")
    exit()

# Open audio streams
try:
    input_stream = p.open(format=INPUT_FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=INPUT_FRAMES_PER_BUFFER)

    output_stream = p.open(format=OUTPUT_FORMAT,
                           channels=CHANNELS,
                           rate=RATE,
                           output=True,
                           frames_per_buffer=OUTPUT_FRAMES_PER_BUFFER)
except Exception as e:
    print(f"Error opening audio streams: {e}")
    if 'p' in locals() and p:
        p.terminate()
    exit()

print(f"Starting as Doctor Agent...")
print("Waiting for initial message from Patient...")

def get_doctor_prompt(patient_message):
    """Generate the doctor receptionist prompt for Gemini"""
    # The persona is a doctor's receptionist handling appointment booking.
    # The extra quote after 'f' has been removed from the line below.
    return f"""You are a helpful and efficient doctor's receptionist. Your goal is to book an appointment for the patient.
Follow these steps:
1. If you don't have it, ask for the patient's full name.
2. Ask for their preferred appointment date and time (offer suggestions if needed).
3. Briefly ask for the reason for the visit (e.g., "check-up", "feeling unwell", "follow-up"). Keep it general unless they offer specifics.
4. Once you have name, date/time preference, and reason, confirm the details back to the patient.
Keep your responses concise (1-2 sentences), polite, and professional.

Current conversation context:
Patient: {patient_message}
Doctor (You):""" # Using "Doctor (You):" to guide the LLM



def chat_with_gemini(prompt):
    """Get response from Gemini API."""
    try:
        # Adjust model as needed (gemini-1.0-pro, gemini-1.5-flash, etc.)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)

        # Basic check for valid response structure
        if response and response.text:
             # Simple clean-up: remove potential markdown like "**"
            cleaned_text = response.text.strip().replace("**", "")
            return cleaned_text
        else:
            print("Warning: Received empty or invalid response from Gemini.")
            return "I'm sorry, I didn't get that. Could you please repeat?"

    except Exception as e:
        print(f"Gemini API Error: {e}")
        # Provide a generic fallback response
        return "I'm having trouble connecting right now. Could you please repeat that?"

# Main loop: Listen for patient, respond as doctor
try:
    while True:
        # Receive and decode message
        try:
            data = input_stream.read(INPUT_FRAMES_PER_BUFFER, exception_on_overflow=False)
            received_text_bytes = ggwave.decode(instance, data)

            if received_text_bytes:
                try:
                    # Attempt to decode the received bytes
                    message = received_text_bytes.decode("utf-8").strip()
                    if not message: # Skip empty messages
                        continue

                    print(f"\nReceived from Patient: {message}")

                    # Generate doctor's response via Gemini
                    prompt = get_doctor_prompt(message)
                    response_text = chat_with_gemini(prompt)
                    print(f"Doctor: {response_text}")

                    # Transmit the doctor's response
                    if response_text:
                        waveform = ggwave.encode(response_text, protocolId=4, volume=VOLUME)
                        if waveform:
                            # Ensure waveform length is a multiple of frame size (bytes per sample * channels)
                            bytes_per_frame = p.get_sample_size(OUTPUT_FORMAT) * CHANNELS
                            num_frames_to_write = len(waveform) // bytes_per_frame
                            output_stream.write(waveform[:num_frames_to_write * bytes_per_frame])
                            print(f"(Transmitting {len(waveform)} bytes...)")
                            time.sleep(TX_PAUSE_DURATION) # Pause after transmitting
                        else:
                            print("Error: Failed to encode response waveform.")
                    else:
                         print("Warning: Skipping transmission of empty response.")


                except UnicodeDecodeError:
                    print("Warning: Received data could not be decoded as UTF-8. Skipping.")
                except Exception as e:
                    print(f"Error during message processing/transmission: {e}")
                    time.sleep(1) # Short pause after an error before listening again

        except IOError as e:
            # Handle potential input overflow errors gracefully
            if e.errno == pyaudio.paInputOverflowed:
                print("Warning: Input overflowed. Skipping.")
            else:
                print(f"Audio read Error: {e}")
                # Consider adding a small delay or break condition if errors persist
                time.sleep(0.1)


except KeyboardInterrupt:
    print("\nStopping Agent...")

# Cleanup
finally:
    print("Cleaning up resources...")
    ggwave.free(instance)
    if 'input_stream' in locals() and input_stream.is_active():
        input_stream.stop_stream()
    if 'input_stream' in locals() and not input_stream.is_stream_stopped():
         input_stream.close()
    if 'output_stream' in locals() and output_stream.is_active():
        output_stream.stop_stream()
    if 'output_stream' in locals() and not output_stream.is_stream_stopped():
        output_stream.close()
    if 'p' in locals() and p:
        p.terminate()
    print("Cleanup complete. Exiting.")