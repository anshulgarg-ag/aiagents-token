import ggwave
import pyaudio
import threading
import time
import sys # To handle potential decoding errors more gracefully

# --- Configuration ---
MESSAGE_TO_SEND = "hello sucker bitch"  # The message you want to send
PROTOCOL_ID = 1                       # ggwave protocol ID
VOLUME = 20                           # Transmission volume (0-100)
SAMPLE_RATE = 48000                   # Audio sample rate
FRAMES_PER_BUFFER = 1024              # Buffer size for both input and output

# --- Transmitter Function ---
def transmit_message(message, protocol_id, volume):
    p_out = None
    stream_out = None
    try:
        print(f"[{threading.current_thread().name}] Initializing transmitter...")
        p_out = pyaudio.PyAudio()

        # Generate audio waveform
        print(f"[{threading.current_thread().name}] Generating waveform for: '{message}'")
        waveform = ggwave.encode(message, protocolId=protocol_id, volume=volume)
        if not waveform:
            print(f"[{threading.current_thread().name}] ERROR: Failed to generate waveform.", file=sys.stderr)
            return

        print(f"[{threading.current_thread().name}] Opening output stream...")
        stream_out = p_out.open(format=pyaudio.paFloat32,
                                channels=1,
                                rate=SAMPLE_RATE,
                                output=True,
                                frames_per_buffer=FRAMES_PER_BUFFER)

        print(f"[{threading.current_thread().name}] Transmitting...")
        # Note: The original calculation len(waveform)//4 is correct because
        # PyAudio paFloat32 uses 4 bytes per frame.
        # However, stream.write expects the number of *frames*, not bytes.
        num_frames = len(waveform) // 4
        stream_out.write(waveform, num_frames)

        # Wait for the stream to finish playing
        # Add a small buffer time based on audio length
        duration_sec = num_frames / SAMPLE_RATE
        time.sleep(duration_sec + 0.5) # Wait for playback + a little extra

        print(f"[{threading.current_thread().name}] Transmission finished.")

    except Exception as e:
        print(f"[{threading.current_thread().name}] ERROR during transmission: {e}", file=sys.stderr)
    finally:
        print(f"[{threading.current_thread().name}] Cleaning up transmitter...")
        if stream_out:
            try:
                stream_out.stop_stream()
            except Exception as e:
                print(f"[{threading.current_thread().name}] Error stopping output stream: {e}", file=sys.stderr)
            try:
                stream_out.close()
            except Exception as e:
                print(f"[{threading.current_thread().name}] Error closing output stream: {e}", file=sys.stderr)
        if p_out:
            try:
                p_out.terminate()
            except Exception as e:
                print(f"[{threading.current_thread().name}] Error terminating PyAudio (out): {e}", file=sys.stderr)
        print(f"[{threading.current_thread().name}] Transmitter cleanup complete.")


# --- Receiver Function ---
def receive_message():
    p_in = None
    stream_in = None
    instance = None
    try:
        print(f"[{threading.current_thread().name}] Initializing receiver...")
        p_in = pyaudio.PyAudio()
        instance = ggwave.init()
        if not instance:
             print(f"[{threading.current_thread().name}] ERROR: Failed to initialize ggwave instance.", file=sys.stderr)
             return

        print(f"[{threading.current_thread().name}] Opening input stream...")
        stream_in = p_in.open(format=pyaudio.paFloat32,
                              channels=1,
                              rate=SAMPLE_RATE,
                              input=True,
                              frames_per_buffer=FRAMES_PER_BUFFER)

        print(f"[{threading.current_thread().name}] Listening... Press Ctrl+C to stop.")
        while True: # Loop indefinitely until KeyboardInterrupt
            try:
                data = stream_in.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                res_bytes = ggwave.decode(instance, data)
                if res_bytes is not None:
                    try:
                        decoded_message = res_bytes.decode("utf-8")
                        print(f"\n[{threading.current_thread().name}] Received text: {decoded_message}")
                    except UnicodeDecodeError:
                        print(f"\n[{threading.current_thread().name}] Received data (not valid UTF-8): {res_bytes}", file=sys.stderr)
                    except Exception as e_decode:
                         print(f"\n[{threading.current_thread().name}] Error processing received data: {e_decode}", file=sys.stderr)

            except IOError as e:
                 # This can happen if the stream is stopped/closed while read() is blocking
                 # Often occurs during shutdown after Ctrl+C
                 if e.errno == pyaudio.paInputOverflowed:
                      print(f"[{threading.current_thread().name}] Warning: Input overflowed.", file=sys.stderr)
                 else:
                      print(f"[{threading.current_thread().name}] IOError during stream read: {e}", file=sys.stderr)
                 # Decide if we should break or continue based on the error
                 # For simplicity here, we'll print and continue, but a real app might break.

    except KeyboardInterrupt:
        print(f"\n[{threading.current_thread().name}] Stopping listener...")
    except Exception as e:
        print(f"[{threading.current_thread().name}] ERROR during reception: {e}", file=sys.stderr)
    finally:
        print(f"[{threading.current_thread().name}] Cleaning up receiver...")
        if instance:
            try:
                ggwave.free(instance)
            except Exception as e:
                 print(f"[{threading.current_thread().name}] Error freeing ggwave instance: {e}", file=sys.stderr)
        if stream_in:
            try:
                stream_in.stop_stream()
            except Exception as e:
                print(f"[{threading.current_thread().name}] Error stopping input stream: {e}", file=sys.stderr)
            try:
                stream_in.close()
            except Exception as e:
                print(f"[{threading.current_thread().name}] Error closing input stream: {e}", file=sys.stderr)
        if p_in:
            try:
                p_in.terminate()
            except Exception as e:
                print(f"[{threading.current_thread().name}] Error terminating PyAudio (in): {e}", file=sys.stderr)
        print(f"[{threading.current_thread().name}] Receiver cleanup complete.")


# --- Main Execution ---
if __name__ == "__main__":
    # Create threads
    receiver_thread = threading.Thread(target=receive_message, name="ReceiverThread")
    transmitter_thread = threading.Thread(target=transmit_message,
                                          args=(MESSAGE_TO_SEND, PROTOCOL_ID, VOLUME),
                                          name="TransmitterThread")

    # Start the receiver first
    receiver_thread.start()

    # Give the receiver a moment to start listening
    time.sleep(1.0) # Adjust if needed

    # Start the transmitter
    transmitter_thread.start()

    # Keep the main thread alive until the receiver thread finishes (e.g., by Ctrl+C)
    # The transmitter thread will finish on its own relatively quickly.
    try:
        receiver_thread.join() # Wait for the receiver thread to exit
    except KeyboardInterrupt:
         print("\n[MainThread] Ctrl+C received in main thread. Exiting.")
         # Note: The receiver thread's KeyboardInterrupt handler should already be running.

    # Optional: Wait for the transmitter thread to ensure it cleans up,
    # though it should finish much earlier than the receiver.
    transmitter_thread.join(timeout=5.0) # Wait max 5 seconds

    print("[MainThread] Program finished.")