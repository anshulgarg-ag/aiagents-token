import ggwave
import pyaudio
import time
import google.generativeai as genai
import sys # Kept for potential future use, though not strictly needed now

# --- Configuration ---
# !!! IMPORTANT: Replace with your actual API key !!!
# Consider using environment variables for security in real applications
GEMINI_API_KEY = "YAIzaSyBSAcDHFF67Zjp-zuywJwWwBnGED30SoVI" # <<< PUT YOUR KEY HERE

# Audio Settings
INPUT_FORMAT = pyaudio.paFloat32
OUTPUT_FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 48000
INPUT_FRAMES_PER_BUFFER = 1024
OUTPUT_FRAMES_PER_BUFFER = 4096 # Larger buffer for potentially longer AI responses

# GGWave Settings
PROTOCOL_ID = 1  # Choose a ggwave protocol (e.g., 1: 'audible-fast')
VOLUME = 20      # Transmission volume (0-100)
TX_PAUSE_DURATION = 2.0 # Seconds to pause after transmitting

# Role (Hardcoded for this version)
ROLE = "doctor"
# --- End Configuration ---


# --- Initialization ---

# Set up Gemini API Key
if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
    print("ERROR: Please replace 'YOUR_GEMINI_API_KEY' with your actual Gemini API key in the script.")
    exit()

try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    print("Please ensure your API key is correct and valid, and the Generative Language API is enabled in your Google Cloud project.")
    exit()

# Initialize PyAudio and GGWave
p = None
instance = None
input_stream = None
output_stream = None
try:
    p = pyaudio.PyAudio()
    instance = ggwave.init()
    if not instance:
         raise RuntimeError("Failed to initialize ggwave instance.")
    print("PyAudio and GGWave initialized.")
except Exception as e:
    print(f"Error initializing PyAudio/GGWave: {e}")
    if p:
        p.terminate()
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
    print("Audio streams opened.")
except Exception as e:
    print(f"Error opening audio streams: {e}")
    if input_stream: input_stream.close()
    if output_stream: output_stream.close()
    if instance: ggwave.free(instance)
    if p: p.terminate()
    exit()

# --- Core Functions ---

def get_doctor_prompt(patient_message):
    """Generate the doctor receptionist prompt for Gemini"""
    # The persona is a doctor's receptionist handling appointment booking.
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
        # Use the stable 'gemini-pro' model identifier (Solution 1)
        # Ensure your google-generativeai library is up to date:
        # pip install --upgrade google-generativeai
        model = genai.GenerativeModel("gemini-pro")

        # Configure safety settings if needed (optional)
        # safety_settings = [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     # Add other categories as needed
        # ]
        # response = model.generate_content(prompt, safety_settings=safety_settings)

        response = model.generate_content(prompt)

        # Basic check for valid response structure
        if response and hasattr(response, 'text') and response.text:
             # Simple clean-up: remove potential markdown like "**" and leading/trailing whitespace
            cleaned_text = response.text.strip().replace("**", "")
            return cleaned_text
        else:
            # Handle cases where response might be blocked or empty
            if response and response.prompt_feedback:
                 print(f"Warning: Gemini response blocked. Reason: {response.prompt_feedback}")
            else:
                 print("Warning: Received empty or invalid response structure from Gemini.")
            return "I'm sorry, I couldn't process that request. Could you rephrase?"

    except Exception as e:
        print(f"Gemini API Error: {e}")
        # Provide a generic fallback response
        return "I'm having trouble connecting right now. Could you please repeat that?"


# --- Main Execution Logic ---

print(f"Starting as Doctor Agent...")
print("Waiting for initial message from Patient...")

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
                    if not message: # Skip empty messages potentially caused by noise
                        continue

                    print(f"\nReceived from Patient: {message}")

                    # Generate doctor's response via Gemini
                    prompt = get_doctor_prompt(message)
                    response_text = chat_with_gemini(prompt)
                    print(f"Doctor: {response_text}")

                    # Transmit the doctor's response
                    if response_text:
                        waveform = ggwave.encode(response_text, protocolId=PROTOCOL_ID, volume=VOLUME)
                        if waveform:
                            # Ensure waveform length is a multiple of frame size (bytes per sample * channels)
                            bytes_per_frame = p.get_sample_size(OUTPUT_FORMAT) * CHANNELS
                            if bytes_per_frame > 0:
                                num_frames_to_write = len(waveform) // bytes_per_frame
                                # Write only complete frames
                                output_stream.write(waveform[:num_frames_to_write * bytes_per_frame])
                                print(f"(Transmitting {len(waveform)} bytes...)")
                                time.sleep(TX_PAUSE_DURATION) # Pause after transmitting
                            else:
                                print("Error: Calculated bytes_per_frame is zero. Cannot write audio.")
                        else:
                            print("Error: Failed to encode response waveform.")
                    else:
                         print("Warning: Skipping transmission of empty or error response.")


                except UnicodeDecodeError:
                    print("Warning: Received data could not be decoded as UTF-8 (possible noise/corruption). Skipping.")
                except Exception as e:
                    print(f"Error during message processing/transmission: {e}")
                    # Avoid busy-looping on rapid errors
                    time.sleep(0.5)

        except IOError as e:
            # Handle potential input overflow errors gracefully
            if e.errno == pyaudio.paInputOverflowed:
                print("Warning: Input overflowed. Data missed.")
            else:
                # Log other IOErrors but continue listening
                print(f"Audio read Error: {e}")
            # Add a small delay to prevent overwhelming the system if errors persist
            time.sleep(0.1)
        except Exception as e:
             print(f"Unexpected error in main loop: {e}")
             time.sleep(1) # Pause after unexpected error

except KeyboardInterrupt:
    print("\nStopping Agent (Keyboard Interrupt)...")

# --- Cleanup ---
finally:
    print("Cleaning up resources...")
    if instance:
        try:
            ggwave.free(instance)
            print("GGWave instance freed.")
        except Exception as e:
            print(f"Error freeing GGWave instance: {e}")

    if input_stream:
        try:
            if input_stream.is_active():
                input_stream.stop_stream()
            input_stream.close()
            print("Input stream closed.")
        except Exception as e:
            print(f"Error closing input stream: {e}")

    if output_stream:
        try:
            if output_stream.is_active():
                output_stream.stop_stream()
            output_stream.close()
            print("Output stream closed.")
        except Exception as e:
            print(f"Error closing output stream: {e}")

    if p:
        try:
            p.terminate()
            print("PyAudio terminated.")
        except Exception as e:
            print(f"Error terminating PyAudio: {e}")

    print("Cleanup attempt complete. Exiting.")