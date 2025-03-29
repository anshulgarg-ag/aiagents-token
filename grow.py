# import ggwave
# import pyaudio
# import requests
# import sys
#
#
# def main():
#     if len(sys.argv) < 2:
#         print("Usage: python script.py <API_URL>")
#         sys.exit(1)
#
#     api_url = sys.argv[1]
#
#     try:
#         response = requests.get(api_url)
#         if response.status_code == 200:
#             message = response.text
#         else:
#             print(f"API returned status code {response.status_code}")
#             sys.exit(1)
#     except requests.exceptions.RequestException as e:
#         print(f"Error fetching from API: {e}")
#         sys.exit(1)
#
#     p = pyaudio.PyAudio()
#
#     # Transmit the message
#     waveform = ggwave.encode(message, protocolId=1, volume=20)
#     stream_out = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, output=True, frames_per_buffer=4096)
#     stream_out.write(waveform, len(waveform) // 4)
#     stream_out.stop_stream()
#     stream_out.close()
#
#     # Receive responses
#     stream_in = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=1024)
#     instance = ggwave.init()
#
#     print('Listening ... Press Ctrl+C to stop')
#     try:
#         while True:
#             data = stream_in.read(1024, exception_on_overflow=False)
#             res = ggwave.decode(instance, data)
#             if res is not None:
#                 try:
#                     print('Received text: ' + res.decode("utf-8"))
#                 except:
#                     pass
#     except KeyboardInterrupt:
#         pass
#
#     ggwave.free(instance)
#     stream_in.stop_stream()
#     stream_in.close()
#     p.terminate()
#
#
# if __name__ == "__main__":
#     main()


import ggwave
import pyaudio
import requests
import sys

def main():
    if len(sys.argv) < 2  or len(sys.argv) > 3:
        print("Usage: python script.py <API_URL> [prompt)")
        exit(1)

    api_url = sys.argv[1]
    if len(sys.argv) == 3:
        prompt = sys.argv[2]
    else:
        prompt = "Generate a message to transmit."

    endpoint_url = f"{api_url}/v1/chat/completions"
    model_name = "lm_studio/llama-3-8b-instruct"
    data = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(endpoint_url, json=data)
        if response.status_code == 200:
            response_json = response.json()
            message = response_json['choices'][0]['message']['content']
        else:
            print(f"Error: API returned status code {response.status_code}")
            exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        exit(1)
    except KeyError as e:
        print(f"Error parsing response: {e}")
        exit(1)

    # Transmit the message
    p = pyaudio.PyAudio()
    waveform = ggwave.encode(message, protocolId=1, volume=20)
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, output=True, frames_per_buffer=4096)
    stream.write(waveform, len(waveform)//4)
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Receive responses
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=1024)
    instance = ggwave.init()

    print('Transmitted message and now listening for responses... Press Ctrl+C to stop')
    try:
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            res = ggwave.decode(instance, data)
            if res is not None:
                try:
                    print('Received text: ' + res.decode("utf-8"))
                except:
                    pass
    except KeyboardInterrupt:
        pass

    ggwave.free(instance)
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()