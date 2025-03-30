import ggwave
import pyaudio
import time
import google.generativeai as genai
import uvicorn
from fastapi import FastAPI, HTTPException

# ... (Your existing configuration and functions: GEMINI_API_KEY,
#      get_doctor_prompt, chat_with_gemini, p, instance,
#      input_stream, output_stream remain the same) ...


app = FastAPI(title="Doctor Appointment Booking API",
              description="API for booking appointments via audio messages using ggwave.",
              version="1.0.0")


@app.post("/process_audio/")
async def process_audio():
    """Processes incoming audio data (ggwave encoded), generates a doctor's response,
       and returns the ggwave encoded audio response.  """
    try:
        # You'll need to modify this part to receive the audio data in a POST request
        # For example, you might receive the audio as base64 encoded data.
        # ... (Receive and decode the base64 encoded audio data) ...
        # received_audio_bytes = base64.b64decode(request.audio_data)

        # Decode ggwave
        message_bytes = ggwave.decode(instance, received_audio_bytes)
        if message_bytes is None:
            raise HTTPException(status_code=400, detail="Invalid ggwave audio data")

        message = message_bytes.decode("utf-8", errors="replace")  # Handle potential decoding errors

        # Generate doctor's response
        prompt = get_doctor_prompt(message)
        response_text = chat_with_gemini(prompt)

        # Encode response using ggwave
        response_audio_bytes = ggwave.encode(response_text, protocolId=PROTOCOL_ID, volume=VOLUME)
        if response_audio_bytes is None:
            raise HTTPException(status_code=500, detail="Error encoding response with ggwave")

        # Encode the audio response to base64 for transmission in the HTTP response
        response_audio_base64 = base64.b64encode(response_audio_bytes).decode("utf-8")

        return {"audio_data": response_audio_base64}

    except HTTPException:
        raise  # Re-raise HTTPExceptions to be handled by FastAPI
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


if __name__ == "__main__":
    print("Starting API server...")
    # Start the FastAPI development server.  For production, use a production-ready ASGI server like Gunicorn or Uvicorn.
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # IMPORTANT: Close audio streams and ggwave instance when the API server shuts down
    # ... (your existing cleanup code from the finally block) ...